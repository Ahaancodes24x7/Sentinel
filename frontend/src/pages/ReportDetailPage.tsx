import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  BadgeCheck,
  Ban,
  CircleAlert,
  FileText,
  PenLine,
  ShieldOff,
  Zap,
} from 'lucide-react';
import {
  Bar,
  Chip,
  PanelHead,
  PulseDot,
  ScanPanel,
  type Tone,
} from '../components/kinetic';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { useReport, useReviewAction } from '../api/hooks';
import { BARRIER_META, BUCKET_META, type BarrierStatus, type Bucket } from '../api/types';
import { cn } from '../lib/cn';

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

/** Colour per extracted field — consistent between the legend and the text. */
const FIELD_TONE: Record<string, Tone> = {
  activity: 'info',
  hazard: 'critical',
  energy_type: 'critical',
  barrier: 'medium',
  barrier_status: 'medium',
  exposure: 'high',
  location: 'violet' as Tone,
};

const FIELD_LABEL: Record<string, string> = {
  activity: 'ACTIVITY',
  hazard: 'HAZARD / ENERGY',
  energy_type: 'ENERGY',
  barrier: 'BARRIER',
  barrier_status: 'BARRIER',
  exposure: 'EXPOSURE',
  location: 'LOCATION',
};

const SPAN_STYLE: Record<string, string> = {
  activity: 'bg-info-wash text-info shadow-[inset_0_-2px_0_var(--color-info)]',
  hazard: 'bg-critical-wash text-critical shadow-[inset_0_-2px_0_var(--color-critical)]',
  energy_type: 'bg-critical-wash text-critical shadow-[inset_0_-2px_0_var(--color-critical)]',
  barrier: 'bg-medium-wash text-medium shadow-[inset_0_-2px_0_var(--color-medium)]',
  barrier_status: 'bg-medium-wash text-medium shadow-[inset_0_-2px_0_var(--color-medium)]',
  exposure: 'bg-high-wash text-high shadow-[inset_0_-2px_0_var(--color-high)]',
  location: 'bg-violet-wash text-violet shadow-[inset_0_-2px_0_var(--color-violet)]',
};

interface Highlight {
  start: number;
  end: number;
  field: string;
  text: string;
  confidence: number;
}

/**
 * Render the report text with extracted spans marked in place.
 *
 * Overlapping spans are resolved by keeping the earliest-starting, then the
 * longest — the extractor can legitimately return a hazard phrase nested
 * inside an activity phrase, and naively slicing both would corrupt the
 * offsets and scramble the text.
 */
function HighlightedText({
  text,
  highlights,
  active,
}: {
  text: string;
  highlights: Highlight[];
  active: string | null;
}) {
  const segments = useMemo(() => {
    const sorted = [...highlights]
      .filter((h) => h.start >= 0 && h.end <= text.length && h.end > h.start)
      .sort((a, b) => a.start - b.start || b.end - a.end);

    const kept: Highlight[] = [];
    let cursor = 0;
    for (const h of sorted) {
      if (h.start >= cursor) {
        kept.push(h);
        cursor = h.end;
      }
    }

    const out: { text: string; field?: string; confidence?: number }[] = [];
    let pos = 0;
    for (const h of kept) {
      if (h.start > pos) out.push({ text: text.slice(pos, h.start) });
      out.push({ text: text.slice(h.start, h.end), field: h.field, confidence: h.confidence });
      pos = h.end;
    }
    if (pos < text.length) out.push({ text: text.slice(pos) });
    return out;
  }, [text, highlights]);

  return (
    <p className="text-base leading-[2] text-ink-2">
      {segments.map((seg, i) =>
        seg.field ? (
          <motion.mark
            key={i}
            className={cn(
              'span-hl cursor-default',
              SPAN_STYLE[seg.field] ?? 'bg-surface-3 text-ink',
              active && active !== seg.field && 'opacity-25',
            )}
            initial={{ backgroundColor: 'rgba(0,0,0,0)' }}
            animate={{ backgroundColor: undefined }}
            transition={{ delay: 0.15 + i * 0.03, duration: 0.4 }}
            title={`${FIELD_LABEL[seg.field] ?? seg.field} · ${((seg.confidence ?? 0) * 100).toFixed(0)}% confidence`}
          >
            {seg.text}
          </motion.mark>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </p>
  );
}

/* -------------------------------------------------------------------------- */

export function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useReport(id);
  const reviewAction = useReviewAction();
  const [activeField, setActiveField] = useState<string | null>(null);
  const [notes, setNotes] = useState('');

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl">
        <PanelLoading rows={10} />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="mx-auto max-w-2xl pt-16">
        <QueryError error={error} />
      </div>
    );
  }

  const cls = data.classification;
  const ext = data.extracted_fields ?? {};
  const bucketTone = BUCKET_TONE[cls.bucket] ?? 'neutral';

  const highlights: Highlight[] = (ext.evidence_spans ?? [])
    .filter((s) => Array.isArray(s.span))
    .map((s) => ({
      start: s.span[0],
      end: s.span[1],
      field: s.field,
      text: s.text,
      confidence: s.confidence ?? 0.7,
    }));

  const barrierLabel = (ext.barrier_status?.label ?? '') as BarrierStatus;
  const barrierMeta = BARRIER_META[barrierLabel];

  const chainSteps = cls.reasoning_chain ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            to="/review-queue"
            className="inline-flex items-center gap-1.5 font-mono text-2xs tracked text-ink-3 hover:text-hivis"
          >
            <ArrowLeft className="h-3 w-3" /> BACK TO QUEUE
          </Link>
          <h1 className="mt-2 flex flex-wrap items-center gap-2.5 font-display text-3xl text-ink">
            <FileText className="h-6 w-6 text-ink-3" strokeWidth={1.8} />
            {data.report_id}
          </h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 font-mono text-2xs text-ink-4">
            <span>{data.site}</span>
            <span>·</span>
            <span>{data.timestamp?.slice(0, 16).replace('T', ' ')}</span>
            <span>·</span>
            <Chip tone={data.source === 'synthetic' ? 'medium' : 'low'}>
              {String(data.source).toUpperCase()}
            </Chip>
          </div>
        </div>

        {/* Verdict card */}
        <div
          className={cn(
            'min-w-[15rem] rounded-panel border p-3',
            cls.sif_potential
              ? 'border-critical-edge bg-critical-wash'
              : 'border-low-edge bg-low-wash',
          )}
        >
          <div className="flex items-center gap-2">
            <PulseDot tone={cls.sif_potential ? 'critical' : 'low'} size={7} />
            <span className="font-mono text-2xs tracked text-ink-2">
              {cls.sif_potential ? 'SIF PRECURSOR' : 'NO PRECURSOR'}
            </span>
          </div>
          <div
            className={cn(
              'mt-1.5 font-display text-3xl',
              cls.sif_potential ? 'text-critical' : 'text-low',
            )}
          >
            {(cls.confidence * 100).toFixed(0)}%
          </div>
          <div className="mt-1 font-mono text-2xs text-ink-4">EVIDENCE STRENGTH</div>
          <Bar
            value={cls.confidence}
            tone={cls.sif_potential ? 'critical' : 'low'}
            className="mt-2"
          />
          <div className="mt-2 flex items-center gap-1.5">
            <Chip tone={bucketTone}>{BUCKET_META[cls.bucket]?.short ?? cls.bucket}</Chip>
            {cls.lsr_tag && cls.lsr_tag !== 'N/A' && <Chip tone="hivis">{cls.lsr_tag}</Chip>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {/* ---------------- Source text with spans ---------------- */}
        <div className="space-y-3 lg:col-span-2">
          <ScanPanel>
            <PanelHead
              title="SOURCE REPORT · EXTRACTED EVIDENCE"
              sub="Every highlight is a character span the model actually used"
              right={<Chip tone="neutral">{highlights.length} SPANS</Chip>}
            />
            <div className="p-5">
              <HighlightedText
                text={data.report_text}
                highlights={highlights}
                active={activeField}
              />
            </div>

            {/* Legend doubles as a filter */}
            <div className="flex flex-wrap gap-1.5 border-t border-line px-5 py-3">
              {Array.from(new Set(highlights.map((h) => h.field))).map((field) => (
                <button
                  key={field}
                  type="button"
                  onMouseEnter={() => setActiveField(field)}
                  onMouseLeave={() => setActiveField(null)}
                  className="transition-transform hover:scale-105"
                >
                  <Chip tone={FIELD_TONE[field] ?? 'neutral'} dot>
                    {FIELD_LABEL[field] ?? field.toUpperCase()}
                  </Chip>
                </button>
              ))}
            </div>
          </ScanPanel>

          {/* ---------------- Justification ---------------- */}
          <ScanPanel>
            <PanelHead
              title="JUSTIFICATION"
              sub="Assembled from the extracted fields — not free text from a model"
              tone="hivis"
            />
            <div className="p-4">
              <p className="text-sm leading-relaxed text-ink-2">{cls.justification}</p>
              <div className="mt-3 font-mono text-2xs text-ink-4">
                model {cls.model_version}
              </div>
            </div>
          </ScanPanel>

          {/* ---------------- Reasoning chain ---------------- */}
          {chainSteps.length > 0 && (
            <ScanPanel>
              <PanelHead
                title="SCL REASONING CHAIN"
                sub="Activity → Energy → Barrier → Exposure → Consequence → Rule"
                tone="info"
              />
              <div className="p-4">
                <ol className="space-y-0">
                  {chainSteps.map((step, i) => (
                    <motion.li
                      key={step.step}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.07, duration: 0.35 }}
                      className="relative flex gap-3 pb-4 last:pb-0"
                    >
                      {i < chainSteps.length - 1 && (
                        <span className="absolute left-[11px] top-6 h-full w-px bg-line" />
                      )}
                      <span className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-line-bright bg-surface-2 font-mono text-2xs text-hivis">
                        {step.step}
                      </span>
                      <div className="min-w-0 pt-0.5">
                        <div className="font-mono text-2xs tracked text-ink-2">{step.label}</div>
                        <div className="mt-0.5 text-xs text-ink-3">{step.detail}</div>
                      </div>
                    </motion.li>
                  ))}
                </ol>
              </div>
            </ScanPanel>
          )}
        </div>

        {/* ---------------- Structured frame + review ---------------- */}
        <div className="space-y-3">
          <ScanPanel>
            <PanelHead title="STRUCTURED EVENT FRAME" tone="info" />
            <div className="divide-y divide-line-faint">
              <FrameRow
                icon={Zap}
                label="ENERGY"
                value={(ext.energy_type?.label as string) ?? '—'}
                confidence={ext.energy_type?.confidence}
                tone="critical"
              />
              <FrameRow
                icon={ShieldOff}
                label="BARRIER"
                value={barrierMeta?.label ?? (ext.barrier_status?.label as string) ?? '—'}
                sub={barrierMeta ? `gap severity ${barrierMeta.gap}` : undefined}
                confidence={ext.barrier_status?.confidence}
                tone={(barrierMeta?.tone as Tone) ?? 'medium'}
              />
              <FrameRow
                icon={CircleAlert}
                label="EXPOSURE"
                value={String(ext.exposure?.label ?? '—').replace(/_/g, ' ')}
                confidence={ext.exposure?.confidence}
                tone="high"
              />
              <FrameRow
                icon={FileText}
                label="ACTIVITY"
                value={(ext.activity?.text as string) ?? (ext.activity?.label as string) ?? '—'}
                confidence={ext.activity?.confidence}
                tone="info"
              />
            </div>
          </ScanPanel>

          {/* Reviewer actions */}
          <ScanPanel>
            <PanelHead
              title="HUMAN REVIEW"
              sub="Corrections enter a retraining queue behind a 2-reviewer gate"
              tone="hivis"
            />
            <div className="space-y-2.5 p-4">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Reviewer notes (optional)…"
                rows={3}
                className="w-full resize-none rounded-md border border-line bg-surface-2 px-2.5 py-2 text-xs text-ink placeholder:text-ink-4 focus:border-hivis-edge focus:outline-none"
              />
              <div className="grid grid-cols-3 gap-1.5">
                <ReviewButton
                  icon={BadgeCheck}
                  label="CONFIRM"
                  tone="low"
                  disabled={reviewAction.isPending}
                  onClick={() =>
                    reviewAction.mutate({ reportId: data.report_id, action: 'confirm', notes })
                  }
                />
                <ReviewButton
                  icon={PenLine}
                  label="CORRECT"
                  tone="medium"
                  disabled={reviewAction.isPending}
                  onClick={() =>
                    reviewAction.mutate({
                      reportId: data.report_id,
                      action: 'correct',
                      correctedSif: !cls.sif_potential,
                      notes,
                    })
                  }
                />
                <ReviewButton
                  icon={Ban}
                  label="REJECT"
                  tone="critical"
                  disabled={reviewAction.isPending}
                  onClick={() =>
                    reviewAction.mutate({ reportId: data.report_id, action: 'reject', notes })
                  }
                />
              </div>
              {reviewAction.isSuccess && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-sm bg-low-wash px-2 py-1.5 font-mono text-2xs tracked text-low"
                >
                  RECORDED · LOGGED TO AUDIT TRAIL
                </motion.div>
              )}
              {reviewAction.isError && (
                <div className="rounded-sm bg-critical-wash px-2 py-1.5 font-mono text-2xs tracked text-critical">
                  ACTION FAILED
                </div>
              )}
            </div>
          </ScanPanel>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function FrameRow({
  icon: Icon,
  label,
  value,
  sub,
  confidence,
  tone = 'neutral',
}: {
  icon: typeof Zap;
  label: string;
  value: string;
  sub?: string;
  confidence?: number;
  tone?: Tone;
}) {
  return (
    <div className="flex items-start gap-2.5 px-4 py-3">
      <Icon
        className={cn(
          'mt-0.5 h-3.5 w-3.5 shrink-0',
          tone === 'critical'
            ? 'text-critical'
            : tone === 'high'
              ? 'text-high'
              : tone === 'medium'
                ? 'text-medium'
                : tone === 'low'
                  ? 'text-low'
                  : 'text-info',
        )}
        strokeWidth={2}
      />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-[9px] tracked text-ink-4">{label}</div>
        <div className="truncate text-sm text-ink" title={value}>
          {value}
        </div>
        {sub && <div className="font-mono text-2xs text-ink-4">{sub}</div>}
      </div>
      {confidence !== undefined && (
        <div className="w-12 shrink-0 text-right">
          <div className="font-mono text-2xs tabular text-ink-3">
            {(confidence * 100).toFixed(0)}%
          </div>
          <Bar value={confidence} tone={tone} height={2} className="mt-1" />
        </div>
      )}
    </div>
  );
}

function ReviewButton({
  icon: Icon,
  label,
  tone,
  onClick,
  disabled,
}: {
  icon: typeof BadgeCheck;
  label: string;
  tone: Tone;
  onClick: () => void;
  disabled?: boolean;
}) {
  const styles: Partial<Record<Tone, string>> = {
    low: 'border-low-edge text-low hover:bg-low-wash',
    medium: 'border-medium-edge text-medium hover:bg-medium-wash',
    critical: 'border-critical-edge text-critical hover:bg-critical-wash',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex flex-col items-center gap-1 rounded-md border px-2 py-2 transition-colors disabled:opacity-40',
        styles[tone],
      )}
    >
      <Icon className="h-3.5 w-3.5" strokeWidth={2} />
      <span className="font-mono text-[9px] tracked">{label}</span>
    </button>
  );
}
