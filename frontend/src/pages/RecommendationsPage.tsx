import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Hammer, ListChecks, ShieldCheck, TriangleAlert, Wrench } from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel, type Tone } from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useRecommendation, useRecommendations } from '../api/hooks';
import { cn } from '../lib/cn';

const PRIORITY_TONE: Record<string, Tone> = {
  HIGH: 'critical',
  MEDIUM: 'high',
  LOW: 'low',
};

/** Hierarchy of controls — the ordering is the point, so it is shown. */
const CONTROL_META: Record<string, { rank: number; tone: Tone; icon: typeof Wrench }> = {
  elimination: { rank: 1, tone: 'low', icon: ShieldCheck },
  substitution: { rank: 2, tone: 'low', icon: ShieldCheck },
  engineering: { rank: 3, tone: 'hivis', icon: Wrench },
  administrative: { rank: 4, tone: 'medium', icon: ListChecks },
  training: { rank: 5, tone: 'high', icon: Hammer },
  ppe: { rank: 6, tone: 'critical', icon: Hammer },
};

export function RecommendationsPage() {
  const [params, setParams] = useSearchParams();
  const { data, isLoading, error } = useRecommendations();
  const recs = data?.recommendations ?? [];

  const [selected, setSelected] = useState<string | null>(params.get('pattern'));
  useEffect(() => {
    if (!selected && recs.length) setSelected(recs[0].pattern_id);
  }, [recs, selected]);

  const { data: detail, isLoading: detailLoading } = useRecommendation(selected ?? undefined);

  function choose(id: string) {
    setSelected(id);
    setParams({ pattern: id });
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">INTERVENTION ENGINE</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Interventions</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          Controls are looked up from a curated, version-controlled library and ranked by the
          hierarchy of controls. Nothing here is generated text — these decide where budget goes,
          so they have to be reviewable and identical between runs.
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
                    selected === rec.pattern_id
                      ? 'bg-hivis-wash'
                      : 'hover:bg-surface-2',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Chip tone={PRIORITY_TONE[rec.priority] ?? 'neutral'} dot>
                      {rec.priority}
                    </Chip>
                    <span className="truncate text-sm text-ink">{rec.title}</span>
                  </div>
                  <p className="mt-1 truncate text-xs text-ink-3">{rec.primary_barrier_failure}</p>
                  <div className="mt-1 font-mono text-2xs text-ink-4">
                    {rec.evidence_summary.report_count} reports ·{' '}
                    {rec.evidence_summary.site_count} sites ·{' '}
                    {rec.evidence_summary.window_days}d
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
                  title="RECOMMENDED CONTROLS"
                  sub="Ordered by hierarchy of controls — engineering above administrative above training"
                  tone="hivis"
                />
                <div className="divide-y divide-line-faint">
                  {detail.recommended_interventions.map((iv, i) => {
                    const meta = CONTROL_META[iv.control_level] ?? CONTROL_META.administrative;
                    const Icon = meta.icon;
                    return (
                      <motion.div
                        key={iv.rank}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06 }}
                        className="flex items-start gap-3 px-4 py-3"
                      >
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-line-bright bg-surface-2 font-mono text-2xs text-hivis">
                          {iv.rank}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-ink">{iv.action}</p>
                          <div className="mt-1 flex items-center gap-1.5">
                            <Chip tone={meta.tone}>
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
