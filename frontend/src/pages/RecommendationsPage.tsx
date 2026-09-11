import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Ban,
  GraduationCap,
  HardHat,
  ListChecks,
  Repeat,
  TriangleAlert,
  Wrench,
  type LucideIcon,
} from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel, TONE_CHIP, type Tone } from '../components/kinetic';
import { Hint } from '../components/common/Hint';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useRecommendation, useRecommendations } from '../api/hooks';
import { cn } from '../lib/cn';

const PRIORITY_TONE: Record<string, Tone> = {
  HIGH: 'critical',
  MEDIUM: 'high',
  LOW: 'low',
};

/**
 * The standard NIOSH/OSHA hierarchy of controls, in rank order. This is the
 * whole framework, not just the tiers this corpus happens to have used yet —
 * a pattern that only ever gets administrative-and-training fixes should
 * visibly show the empty elimination/engineering tiers above it, not hide
 * the fact that a stronger control was never on the table.
 */
interface ControlTier {
  key: string;
  label: string;
  icon: LucideIcon;
  tone: Tone;
  blurb: string;
}
const CONTROL_TIERS: ControlTier[] = [
  {
    key: 'elimination',
    label: 'Elimination',
    icon: Ban,
    tone: 'low',
    blurb: 'Remove the hazard entirely so no control is needed. Most effective — and rarely feasible on a live facility.',
  },
  {
    key: 'substitution',
    label: 'Substitution',
    icon: Repeat,
    tone: 'low',
    blurb: 'Replace the hazard with something less dangerous — a lower-pressure test method, a non-flammable solvent.',
  },
  {
    key: 'engineering',
    label: 'Engineering',
    icon: Wrench,
    tone: 'hivis',
    blurb: 'Redesign the workplace or equipment so the hazard physically cannot reach a person — guarding, isolation points, barricades.',
  },
  {
    key: 'administrative',
    label: 'Administrative',
    icon: ListChecks,
    tone: 'medium',
    blurb: 'Change how people work around a hazard that still exists — permits, checklists, spot audits, scheduling.',
  },
  {
    key: 'training',
    label: 'Training',
    icon: GraduationCap,
    tone: 'high',
    blurb: 'Teach people to recognise and respond to a hazard that still exists. Necessary, but depends on it being remembered under pressure.',
  },
  {
    key: 'ppe',
    label: 'PPE',
    icon: HardHat,
    tone: 'critical',
    blurb: 'Personal protective equipment — the last layer, relied on only after every control above it has been considered.',
  },
];
const TIER_BY_KEY = Object.fromEntries(CONTROL_TIERS.map((t) => [t.key, t]));
const STRONG_TIERS = new Set(['elimination', 'substitution', 'engineering']);

/**
 * The pyramid is the connective tissue between "here is a ranked list of
 * actions" and "here is WHY they're ranked that way". Clicking a tier filters
 * the list below to it; tiers this pattern never reaches for stay visible
 * but dim, so the gap is legible rather than hidden.
 */
function ControlPyramid({
  tierCounts,
  focus,
  onFocus,
}: {
  tierCounts: Record<string, number>;
  focus: string | null;
  onFocus: (key: string | null) => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-sm flex-col items-center gap-1 py-1">
      {CONTROL_TIERS.map((tier, i) => {
        const count = tierCounts[tier.key] ?? 0;
        const isFocus = focus === tier.key;
        const Icon = tier.icon;
        return (
          <Hint key={tier.key} content={tier.blurb} side="right" delay={250} className="w-full justify-center">
            <motion.button
              type="button"
              onClick={() => onFocus(isFocus ? null : tier.key)}
              style={{ width: `${42 + i * 9.5}%` }}
              initial={{ opacity: 0, scaleX: 0.85 }}
              animate={{ opacity: count > 0 ? 1 : 0.4, scaleX: 1 }}
              transition={{ delay: i * 0.05, duration: 0.4 }}
              className={cn(
                'flex items-center justify-between gap-2 rounded-sm border px-3 py-1.5',
                'font-mono text-2xs tracked transition-[filter,box-shadow]',
                TONE_CHIP[tier.tone],
                isFocus && 'shadow-[0_0_0_2px_var(--color-hivis)]',
              )}
            >
              <span className="flex items-center gap-1.5">
                <Icon className="h-3 w-3 shrink-0" strokeWidth={2.2} />
                {tier.label}
              </span>
              <span className="tabular">{count}</span>
            </motion.button>
          </Hint>
        );
      })}
    </div>
  );
}

export function RecommendationsPage() {
  const [params, setParams] = useSearchParams();
  const { data, isLoading, error } = useRecommendations();
  const recs = data?.recommendations ?? [];

  const [selected, setSelected] = useState<string | null>(params.get('pattern'));
  useEffect(() => {
    if (!selected && recs.length) setSelected(recs[0].pattern_id);
  }, [recs, selected]);

  const { data: detail, isLoading: detailLoading } = useRecommendation(selected ?? undefined);
  const [pyramidFocus, setPyramidFocus] = useState<string | null>(null);

  function choose(id: string) {
    setSelected(id);
    setParams({ pattern: id });
    setPyramidFocus(null);
  }

  const tierCounts = useMemo(() => {
    const m: Record<string, number> = {};
    (detail?.recommended_interventions ?? []).forEach((iv) => {
      m[iv.control_level] = (m[iv.control_level] ?? 0) + 1;
    });
    return m;
  }, [detail]);

  const strongCount = (detail?.recommended_interventions ?? []).filter((iv) =>
    STRONG_TIERS.has(iv.control_level),
  ).length;
  const totalIv = detail?.recommended_interventions.length ?? 0;

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">INTERVENTION ENGINE</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Interventions</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          Controls are looked up from a curated, version-controlled library and ranked by the{' '}
          <strong className="text-ink-2">hierarchy of controls</strong> — engineering and above outrank
          administrative fixes, which outrank training and PPE. Nothing here is generated text: these decide
          where budget goes, so they have to be reviewable and identical between runs.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
        {/* Pattern list */}
        <ScanPanel className="lg:col-span-2">
          <PanelHead
            title="RANKED PATTERNS"
            sub="Priority from evidence weight, not a tuned score"
            right={<Chip tone="neutral">{recs.length}</Chip>}
          />
          {isLoading ? (
            <PanelLoading rows={6} />
          ) : error ? (
            <QueryError error={error} />
          ) : recs.length === 0 ? (
            <EmptyPanel
              title="No patterns detected"
              message="Run RECOMPUTE in the top bar after ingesting reports."
            />
          ) : (
            <div className="max-h-[34rem] divide-y divide-line-faint overflow-y-auto">
              {recs.map((rec, i) => (
                <motion.button
                  key={rec.pattern_id}
                  type="button"
                  onClick={() => choose(rec.pattern_id)}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className={cn(
                    'block w-full px-4 py-3 text-left transition-colors',
                    selected === rec.pattern_id ? 'bg-hivis-wash' : 'hover:bg-surface-2',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Chip tone={PRIORITY_TONE[rec.priority] ?? 'neutral'} dot>
                      {rec.priority}
                    </Chip>
                    <span className="truncate text-sm text-ink">{rec.title}</span>
                  </div>
                  <p className="mt-1 truncate text-xs text-ink-3">{rec.primary_barrier_failure}</p>
                  <div className="mt-1 flex items-center gap-1.5 font-mono text-2xs text-ink-4">
                    <span>{rec.evidence_summary.report_count} reports</span>
                    <span>·</span>
                    <span>{rec.evidence_summary.site_count} sites</span>
                    <span>·</span>
                    <span>{rec.evidence_summary.window_days}d</span>
                    {rec.primary_lsr && rec.primary_lsr !== 'N/A' && (
                      <Chip tone="violet" className="ml-auto">
                        {rec.primary_lsr}
                      </Chip>
                    )}
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </ScanPanel>

        {/* Detail */}
        <div className="space-y-3 lg:col-span-3">
          {detailLoading ? (
            <ScanPanel>
              <PanelLoading rows={8} />
            </ScanPanel>
          ) : !detail ? (
            <ScanPanel>
              <EmptyPanel title="Select a pattern" />
            </ScanPanel>
          ) : (
            <>
              <ScanPanel>
                <PanelHead title="EVIDENCE TRAIL" sub={detail.title} tone="critical" />

                {/* Connectivity breadcrumb: this pattern traces to one curated
                    barrier, which traces to one IOGP rule — click through. */}
                <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5 font-mono text-2xs tracked text-ink-4">
                  <span className="text-hivis">PATTERN</span>
                  <ArrowRight className="h-3 w-3 shrink-0" />
                  <span className="normal-case tracking-normal text-ink-2">{detail.barrier_type}</span>
                  <ArrowRight className="h-3 w-3 shrink-0" />
                  {detail.primary_lsr && detail.primary_lsr !== 'N/A' ? (
                    <Link
                      to={`/life-saving-rules?rule=${encodeURIComponent(detail.primary_lsr)}`}
                      className="text-hivis hover:underline"
                    >
                      {detail.primary_lsr.toUpperCase()}
                    </Link>
                  ) : (
                    <span>RULE NOT RESOLVED</span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
                  <Metric label="REPORTS" value={detail.evidence.report_count} />
                  <Metric label="SITES" value={detail.evidence.site_count} />
                  <Metric label="WINDOW (DAYS)" value={detail.evidence.window_days} />
                  <Metric
                    label="INTERVENTIONS"
                    value={detail.recommended_interventions.length}
                  />
                </div>

                {/* Breakdown — counts only, never causal language */}
                <div className="border-t border-line px-4 py-3">
                  <div className="font-mono text-[9px] tracked text-ink-4">
                    WHAT THE REPORTS SAY
                  </div>
                  <div className="mt-2 space-y-1.5">
                    {Object.entries(detail.evidence.breakdown)
                      .filter(([k]) => !k.startsWith('failure_mode::'))
                      .slice(0, 6)
                      .map(([key, count]) => {
                        const share = detail.evidence.report_count
                          ? count / detail.evidence.report_count
                          : 0;
                        return (
                          <div key={key}>
                            <div className="flex justify-between text-xs">
                              <span className="text-ink-2">{key.replace(/_/g, ' ')}</span>
                              <span className="font-mono tabular text-ink-3">
                                {count}/{detail.evidence.report_count}
                              </span>
                            </div>
                            <Bar
                              value={share}
                              tone={share > 0.6 ? 'critical' : share > 0.3 ? 'high' : 'medium'}
                              height={3}
                              className="mt-1"
                            />
                          </div>
                        );
                      })}
                  </div>
                </div>

                <div className="flex flex-wrap gap-1 border-t border-line px-4 py-3">
                  {detail.evidence.sites.map((s) => (
                    <Chip key={s} tone="neutral">
                      {s}
                    </Chip>
                  ))}
                </div>
              </ScanPanel>

              <ScanPanel>
                <PanelHead
                  title="HIERARCHY OF CONTROLS"
                  sub="Where this pattern's recommended controls actually sit — click a tier to filter the list"
                  tone="hivis"
                  right={
                    totalIv > 0 ? (
                      <Chip tone={strongCount > 0 ? 'low' : 'medium'}>
                        {strongCount}/{totalIv} ENGINEERING+
                      </Chip>
                    ) : undefined
                  }
                />
                <div className="p-4">
                  <ControlPyramid tierCounts={tierCounts} focus={pyramidFocus} onFocus={setPyramidFocus} />
                </div>

                <div className="divide-y divide-line-faint border-t border-line">
                  {detail.recommended_interventions.map((iv, i) => {
                    const tier = TIER_BY_KEY[iv.control_level] ?? TIER_BY_KEY.administrative;
                    const Icon = tier.icon;
                    const dimmed = pyramidFocus !== null && iv.control_level !== pyramidFocus;
                    return (
                      <motion.div
                        key={iv.rank}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: dimmed ? 0.32 : 1, y: 0 }}
                        transition={{ delay: i * 0.06, opacity: { duration: 0.25 } }}
                        className="flex items-start gap-3 px-4 py-3"
                      >
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-line-bright bg-surface-2 font-mono text-2xs text-hivis">
                          {iv.rank}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-ink">{iv.action}</p>
                          <div className="mt-1 flex items-center gap-1.5">
                            <Chip tone={tier.tone}>
                              <Icon className="h-2.5 w-2.5" />
                              {iv.control_level.toUpperCase()}
                            </Chip>
                            <Chip tone={PRIORITY_TONE[iv.priority] ?? 'neutral'}>
                              {iv.priority}
                            </Chip>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>

                <div className="space-y-2 border-t border-line px-4 py-3">
                  <div>
                    <div className="font-mono text-[9px] tracked text-ink-4">OBJECTIVE</div>
                    <p className="mt-0.5 text-sm text-ink-2">{detail.expected_objective}</p>
                  </div>
                  <div className="flex items-start gap-2 rounded-md border border-medium-edge bg-medium-wash px-3 py-2">
                    <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0 text-medium" strokeWidth={2} />
                    <p className="text-2xs text-ink-2">
                      Evidence shown is co-occurrence in reported observations, not a demonstrated
                      causal relationship. No effectiveness claim is made for any control.
                    </p>
                  </div>
                </div>
              </ScanPanel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="font-mono text-[9px] tracked text-ink-4">{label}</div>
      <div className="font-display text-2xl text-ink">
        <Counter value={value} />
      </div>
    </div>
  );
}
