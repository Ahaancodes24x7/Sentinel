import { motion } from 'framer-motion';
import { Gauge, ShieldQuestion, Target } from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { useHealth, useSummary } from '../api/hooks';
import { BUCKET_META, type Bucket } from '../api/types';

const BUCKET_TONE: Record<Bucket, 'critical' | 'high' | 'medium' | 'low'> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

/**
 * Live routing behaviour, not a metrics dump.
 *
 * Offline evaluation numbers (F2, PR-AUC, ECE, span F1) live in
 * `aiml/reports/model_evaluation_report.md`, produced by the training run.
 * Hardcoding them into the UI would mean the screen keeps asserting a score
 * long after the model behind it changed — so this page shows what the
 * deployed model is doing right now, and points at the report for the rest.
 */
export function ModelPerformancePage() {
  const { data: health, isLoading, error } = useHealth();
  const { data: summary } = useSummary();

  const counts = (summary?.bucket_counts as Record<string, number>) ?? {};
  const total = summary?.total_reports ?? 0;
  const buckets = Object.keys(BUCKET_META) as Bucket[];

  const reviewQueue =
    (counts.HIGH_CONF_SIF ?? 0) + (counts.LOW_CONF_REVIEW ?? 0) + (counts.NEEDS_MORE_INFO ?? 0);
  const queueShare = total ? reviewQueue / total : 0;

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">MODEL OBSERVABILITY</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Model Performance</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          What the deployed model is doing on the live corpus. Held-out evaluation metrics — F2,
          PR-AUC, calibration error, span F1 — are produced by the training run and written to{' '}
          <code className="rounded-sm bg-surface-2 px-1 font-mono text-xs text-ink-2">
            aiml/reports/model_evaluation_report.md
          </code>
          .
        </p>
      </div>

      {isLoading ? (
        <ScanPanel>
          <PanelLoading rows={5} />
        </ScanPanel>
      ) : error ? (
        <QueryError error={error} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <ScanPanel className="p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[9px] tracked text-ink-4">ACTIVE MODEL</span>
                <Gauge className="h-3.5 w-3.5 text-hivis" strokeWidth={2} />
              </div>
              <div className="mt-2 font-mono text-lg text-ink">
                {health?.model_version ?? '—'}
              </div>
              <div className="mt-0.5 font-mono text-2xs text-ink-4">
                {health?.active_sif_model ?? 'baseline2'}
              </div>
            </ScanPanel>

            <ScanPanel className="p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[9px] tracked text-ink-4">REPORTS SCORED</span>
                <Target className="h-3.5 w-3.5 text-info" strokeWidth={2} />
              </div>
              <div className="mt-2 font-display text-3xl text-ink">
                <Counter value={total} />
              </div>
            </ScanPanel>

            <ScanPanel className="p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[9px] tracked text-ink-4">REVIEW QUEUE LOAD</span>
                <ShieldQuestion className="h-3.5 w-3.5 text-high" strokeWidth={2} />
              </div>
              <div className="mt-2 font-display text-3xl text-high">
                <Counter value={queueShare * 100} decimals={1} suffix="%" />
              </div>
              <Bar value={queueShare} tone="high" className="mt-2" />
            </ScanPanel>

            <ScanPanel className="p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[9px] tracked text-ink-4">PRECURSOR RATE</span>
                <PulseDot tone="critical" size={6} />
              </div>
              <div className="mt-2 font-display text-3xl text-critical">
                <Counter value={(summary?.sif_rate ?? 0) * 100} decimals={1} suffix="%" />
              </div>
              <Bar value={summary?.sif_rate ?? 0} tone="critical" className="mt-2" />
            </ScanPanel>
          </div>

          <ScanPanel>
            <PanelHead
              title="LIVE ROUTING DISTRIBUTION"
              sub="Where the deployed model is actually sending reports"
            />
            <div className="space-y-3 p-4">
              {buckets.map((bucket, i) => {
                const value = counts[bucket] ?? 0;
                const share = total ? value / total : 0;
                return (
                  <motion.div
                    key={bucket}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <div className="flex items-baseline justify-between">
                      <div className="flex items-center gap-2">
                        <PulseDot tone={BUCKET_TONE[bucket]} size={6} live={false} />
                        <span className="text-sm text-ink">{BUCKET_META[bucket].label}</span>
                        <Chip tone={BUCKET_TONE[bucket]}>{BUCKET_META[bucket].short}</Chip>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-sm tabular text-ink">
                          <Counter value={value} />
                        </span>
                        <span className="w-12 text-right font-mono text-2xs tabular text-ink-4">
                          {(share * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <Bar value={share} tone={BUCKET_TONE[bucket]} className="mt-1.5" delay={i * 0.06} />
                  </motion.div>
                );
              })}
            </div>
          </ScanPanel>

          <ScanPanel>
            <PanelHead title="EVALUATION POSTURE" tone="medium" />
            <div className="space-y-3 p-4 text-sm text-ink-2">
              <p>
                <strong className="text-ink">Optimised for recall, not accuracy.</strong> The
                positive class is a minority and a missed precursor is categorically worse than an
                extra human review, so the operating threshold is chosen on validation as the
                highest one still achieving the required recall — never the one that maximises
                accuracy.
              </p>
              <p>
                <strong className="text-ink">Calibration is measured separately.</strong> Ranking
                quality and probability quality are different properties. The 4-bucket routing is
                only meaningful if a stated confidence of 0.9 is right about 90% of the time, so
                Expected Calibration Error is reported alongside PR-AUC.
              </p>
            </div>
          </ScanPanel>
        </>
      )}
    </div>
  );
}
