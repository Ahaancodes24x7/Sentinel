import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Inbox, Timer } from 'lucide-react';
import {
  Bar,
  Chip,
  Counter,
  LiveFeed,
  PanelHead,
  PulseDot,
  ScanPanel,
  type Tone,
} from '../components/kinetic';
import { EmptyPanel, NoDataYet, PanelLoading, QueryError } from '../components/common/QueryState';
import { useReviewQueue, useSummary } from '../api/hooks';
import { BUCKET_META, type Bucket } from '../api/types';
import { cn } from '../lib/cn';

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

type SortKey = 'oldest' | 'newest' | 'confidence_asc';

export function ReviewQueuePage() {
  const [sort, setSort] = useState<SortKey>('oldest');
  const { data, isLoading, error, isFetching } = useReviewQueue(undefined, sort, 60);
  const { data: summary } = useSummary();

  const items = data?.items ?? [];
  const counts = (summary?.bucket_counts as Record<string, number>) ?? {};

  const priority = items.filter((r) => r.bucket === 'HIGH_CONF_SIF');
  const standard = items.filter((r) => r.bucket === 'LOW_CONF_REVIEW');
  const incomplete = items.filter((r) => r.bucket === 'NEEDS_MORE_INFO');

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="critical" size={7} />
            <span className="font-mono text-2xs tracked text-ink-4">
              HUMAN-IN-THE-LOOP · LIVE QUEUE
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">Review Queue</h1>
          <p className="mt-1.5 max-w-2xl text-sm text-ink-3">
            Recall-optimised routing. The system accepts extra review rather than risk missing a
            precursor — a false negative here is categorically worse than a false positive.
          </p>
        </div>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          className="rounded-md border border-line bg-surface-2 px-2.5 py-1.5 text-xs text-ink focus:border-hivis-edge focus:outline-none"
        >
          <option value="oldest">Oldest first</option>
          <option value="newest">Newest first</option>
          <option value="confidence_asc">Lowest confidence first</option>
        </select>
      </div>

      {/* Bucket summary strip */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <QueueTile
          label="PRIORITY REVIEW"
          detail="High-confidence precursor"
          value={counts.HIGH_CONF_SIF ?? priority.length}
          tone="critical"
        />
        <QueueTile
          label="STANDARD REVIEW"
          detail="Candidate with unverified evidence"
          value={counts.LOW_CONF_REVIEW ?? standard.length}
          tone="high"
        />
        <QueueTile
          label="NEEDS MORE DETAIL"
          detail="Report quality gap, not a verdict"
          value={counts.NEEDS_MORE_INFO ?? incomplete.length}
          tone="medium"
        />
      </div>

      <ScanPanel className="flex flex-col">
        <PanelHead
          title="TRIAGE STREAM"
          sub="Oldest-first by default so nothing ages out unseen"
          tone="critical"
          right={
            isFetching ? (
              <span className="flex items-center gap-1.5">
                <PulseDot tone="hivis" size={5} />
                <span className="font-mono text-2xs tracked text-ink-4">POLLING</span>
              </span>
            ) : (
              <Chip tone="neutral">{data?.total ?? 0} QUEUED</Chip>
            )
          }
        />

        {isLoading ? (
          <PanelLoading rows={8} />
        ) : error ? (
          <QueryError error={error} />
        ) : (data?.total ?? 0) === 0 ? (
          <NoDataYet />
        ) : items.length === 0 ? (
          <EmptyPanel icon={Inbox} title="Queue clear" message="Nothing is waiting for review." />
        ) : (
          <LiveFeed
            items={items}
            max={40}
            keyFor={(r) => r.report_id}
            renderItem={(r) => (
              <Link
                to={`/reports/${r.report_id}`}
                className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-2"
              >
                <PulseDot
                  tone={BUCKET_TONE[r.bucket]}
                  size={7}
                  live={r.bucket === 'HIGH_CONF_SIF'}
                />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-ink group-hover:text-hivis">
                      {r.report_id}
                    </span>
                    <Chip tone={BUCKET_TONE[r.bucket]}>
                      {BUCKET_META[r.bucket]?.short ?? r.bucket}
                    </Chip>
                    {r.lsr_tag && r.lsr_tag !== 'N/A' && <Chip tone="hivis">{r.lsr_tag}</Chip>}
                  </div>
                  <div className="mt-1 flex items-center gap-2 font-mono text-2xs text-ink-4">
                    <span>{r.site}</span>
                    <span>·</span>
                    <span className="flex items-center gap-1">
                      <Timer className="h-2.5 w-2.5" />
                      {r.timestamp?.slice(0, 10)}
                    </span>
                  </div>
                </div>

                {typeof r.confidence === 'number' && (
                  <div className="hidden w-20 shrink-0 sm:block">
                    <div className="text-right font-mono text-2xs tabular text-ink-3">
                      {(r.confidence * 100).toFixed(0)}%
                    </div>
                    <Bar value={r.confidence} tone={BUCKET_TONE[r.bucket]} height={3} className="mt-1" />
                  </div>
                )}

                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-ink-4 transition-transform group-hover:translate-x-0.5 group-hover:text-hivis" />
              </Link>
            )}
          />
        )}
      </ScanPanel>

      <p className="text-xs text-ink-4">
        Reviewer decisions are logged with actor and timestamp. Corrections enter a retraining
        queue and are only promoted into the training set once two independent reviewers agree —
        a single mislabel cannot degrade the model.
      </p>
    </div>
  );
}

function QueueTile({
  label,
  detail,
  value,
  tone,
}: {
  label: string;
  detail: string;
  value: number;
  tone: Tone;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'rounded-panel border p-4',
        tone === 'critical'
          ? 'border-critical-edge bg-critical-wash'
          : tone === 'high'
            ? 'border-high-edge bg-high-wash'
            : 'border-medium-edge bg-medium-wash',
      )}
    >
      <div className="flex items-center gap-2">
        <PulseDot tone={tone} size={6} live={tone === 'critical'} />
        <span className="font-mono text-2xs tracked text-ink-2">{label}</span>
      </div>
      <div className="mt-1.5 font-display text-4xl text-ink">
        <Counter value={value} />
      </div>
      <div className="mt-0.5 text-xs text-ink-3">{detail}</div>
    </motion.div>
  );
}
