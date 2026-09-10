import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Siren } from 'lucide-react';
import { Chip, Counter, PanelHead, PulseDot, ScanPanel, type Tone } from '../components/kinetic';
import { EmptyPanel, NoDataYet, PanelLoading, QueryError } from '../components/common/QueryState';
import { useReports, useSummary } from '../api/hooks';
import { BUCKET_META, type Bucket } from '../api/types';
import { ALL_SITES, useSelectedSite } from '../lib/siteContext';

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

export function SIFPrecursorsPage() {
  const { selectedSite } = useSelectedSite();
  const siteParam = selectedSite.site_id !== ALL_SITES.site_id ? selectedSite.site_id : undefined;
  const { data, isLoading, error } = useReports({ site: siteParam, sif_potential: true, limit: 60 });
  const { data: summary } = useSummary(siteParam);
  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="critical" size={7} />
            <span className="font-mono text-2xs tracked text-ink-4">
              REQUIREMENT (A) · CLASSIFICATION ·{' '}
              {siteParam ? selectedSite.canonical_name.toUpperCase() : 'ALL SITES'}
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">SIF Precursors</h1>
          <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
            Every report here carries credible fatal potential regardless of what actually happened.
            Most caused no injury at all — that is precisely the point.
          </p>
        </div>
        <div className="text-right">
          <div className="font-display text-5xl text-critical">
            <Counter value={summary?.sif_flagged_count ?? data?.total ?? 0} />
          </div>
          <div className="font-mono text-2xs tracked text-ink-4">
            FLAGGED · {((summary?.sif_rate ?? 0) * 100).toFixed(1)}% OF CORPUS
          </div>
        </div>
      </div>

      <ScanPanel>
        <PanelHead
          title="FLAGGED OBSERVATIONS"
          tone="critical"
          right={<Chip tone="critical">{data?.total ?? 0}</Chip>}
        />
        {isLoading ? (
          <PanelLoading rows={10} />
        ) : error ? (
          <QueryError error={error} />
        ) : (data?.total ?? 0) === 0 ? (
          <NoDataYet />
        ) : items.length === 0 ? (
          <EmptyPanel icon={Siren} title="No precursors flagged" />
        ) : (
          <div className="divide-y divide-line-faint">
            {items.map((r, i) => (
              <motion.div
                key={r.report_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.02, 0.4) }}
              >
                <Link
                  to={`/reports/${r.report_id}`}
                  className="group flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-surface-2"
                >
                  <PulseDot
                    tone={BUCKET_TONE[r.bucket]}
                    size={6}
                    live={r.bucket === 'HIGH_CONF_SIF'}
                  />
                  <span className="font-mono text-xs text-ink group-hover:text-hivis">
                    {r.report_id}
                  </span>
                  <Chip tone={BUCKET_TONE[r.bucket]}>
                    {BUCKET_META[r.bucket]?.short ?? r.bucket}
                  </Chip>
                  <span className="truncate text-xs text-ink-2">{r.lsr_tag}</span>
                  <span className="ml-auto shrink-0 font-mono text-2xs text-ink-4">{r.site}</span>
                  <span className="shrink-0 font-mono text-2xs tabular text-ink-4">
                    {r.timestamp?.slice(0, 10)}
                  </span>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </ScanPanel>
    </div>
  );
}
