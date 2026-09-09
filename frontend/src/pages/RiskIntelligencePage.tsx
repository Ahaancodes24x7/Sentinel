import { useState } from 'react';
import { motion } from 'framer-motion';
import { Scale, TrendingDown, TrendingUp } from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useRankings } from '../api/hooks';
import { cn } from '../lib/cn';

const COMPONENT_LABEL: Record<string, string> = {
  psif_rate: 'Precursor rate',
  barrier_gap: 'Barrier gap severity',
  energy_magnitude: 'Energy magnitude',
  pattern_recurrence: 'Pattern recurrence',
  reporting_culture_penalty: 'Reporting-culture correction',
};

export function RiskIntelligencePage() {
  const [metric, setMetric] = useState<'simple' | 'composite'>('composite');
  const [groupBy, setGroupBy] = useState<'site' | 'activity'>('site');
  const { data, isLoading, error } = useRankings(metric, groupBy);

  const rows = data?.rankings ?? [];
  const max = Math.max(...rows.map((r) => r.density), 0.0001);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="hivis" size={6} />
            <span className="font-mono text-2xs tracked text-ink-4">
              EXPECTED OUTCOME · DENSITY RANKING
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">Site Risk</h1>
          <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
            A site with 50 reports that are consistently “barrier confirmed” is safer than one with
            10 where six show an absent barrier. Density is built from barrier state, not report
            volume.
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          {/* Metric toggle — the methodological-honesty control */}
          <div className="flex rounded-md border border-line bg-surface-2 p-0.5">
            {(['simple', 'composite'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMetric(m)}
                className={cn(
                  'relative rounded-sm px-3 py-1 font-mono text-2xs tracked transition-colors',
                  metric === m ? 'text-on-hivis' : 'text-ink-3 hover:text-ink',
                )}
              >
                {metric === m && (
                  <motion.span
                    layoutId="metric-pill"
                    className="absolute inset-0 rounded-sm bg-hivis"
                    transition={{ type: 'spring', stiffness: 480, damping: 34 }}
                  />
                )}
                <span className="relative">{m.toUpperCase()}</span>
              </button>
            ))}
          </div>
          <div className="flex rounded-md border border-line bg-surface-2 p-0.5">
            {(['site', 'activity'] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGroupBy(g)}
                className={cn(
                  'rounded-sm px-3 py-1 font-mono text-2xs tracked transition-colors',
                  groupBy === g ? 'bg-surface-hi text-ink' : 'text-ink-3 hover:text-ink',
                )}
              >
                BY {g.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Methodology note — always visible, never a hover tooltip */}
      {data?.note && (
        <div
          className={cn(
            'flex items-start gap-2 rounded-panel border px-4 py-2.5',
            metric === 'composite'
              ? 'border-medium-edge bg-medium-wash'
              : 'border-info-edge bg-info-wash',
          )}
        >
          <Scale
            className={cn(
              'mt-0.5 h-3.5 w-3.5 shrink-0',
              metric === 'composite' ? 'text-medium' : 'text-info',
            )}
            strokeWidth={2}
          />
          <div>
            <p className="text-xs text-ink-2">{data.note}</p>
            {metric === 'composite' && data.weights && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {Object.entries(data.weights).map(([k, v]) => (
                  <Chip key={k} tone="neutral">
                    {COMPONENT_LABEL[k] ?? k} {v}
                  </Chip>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <ScanPanel>
        <PanelHead
          title={`${groupBy.toUpperCase()} RANKING`}
          sub={`${metric} metric · ${data?.window_days ?? 42}-day window`}
          right={<Chip tone={data?.calibrated ? 'low' : 'medium'}>
            {data?.calibrated ? 'CALIBRATED' : 'UNCALIBRATED'}
          </Chip>}
        />

        {isLoading ? (
          <PanelLoading rows={8} />
        ) : error ? (
          <QueryError error={error} />
        ) : rows.length === 0 ? (
          <EmptyPanel title="No data in this window" />
        ) : (
          <div className="divide-y divide-line-faint">
            {rows.map((row, i) => (
              <motion.div
                key={row.group}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-2xs tabular text-ink-4">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span className="text-sm text-ink">{row.group}</span>
                    <Chip tone="neutral">{row.primary_lsr}</Chip>
                  </div>

                  <div className="flex items-baseline gap-4">
                    {row.trend_direction !== 'flat' && (
                      <span
                        className={cn(
                          'flex items-center gap-1 font-mono text-2xs',
                          row.trend_direction === 'up' ? 'text-critical' : 'text-low',
                        )}
                      >
                        {row.trend_direction === 'up' ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        {Math.abs(row.trend_pct).toFixed(0)}%
                      </span>
                    )}
                    <span className="font-mono text-2xs tabular text-ink-3">
                      {row.sif_flagged_count}/{row.total_reports}
                    </span>
                    <span className="font-display text-xl text-hivis">
                      <Counter value={row.density} decimals={3} />
                    </span>
                  </div>
                </div>

                <Bar
                  value={row.density / max}
                  tone={i === 0 ? 'critical' : i < 3 ? 'high' : 'hivis'}
                  delay={i * 0.03}
                  className="mt-2"
                />

                {/* Component breakdown — never a bare score */}
                {metric === 'composite' && Object.keys(row.components).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                    {Object.entries(row.components).map(([key, value]) => (
                      <span key={key} className="font-mono text-[9px] text-ink-4">
                        {COMPONENT_LABEL[key] ?? key}{' '}
                        <span
                          className={cn(
                            'tabular',
                            key === 'reporting_culture_penalty' ? 'text-low' : 'text-ink-2',
                          )}
                        >
                          {key === 'reporting_culture_penalty' && value > 0 ? '−' : ''}
                          {value.toFixed(3)}
                        </span>
                      </span>
                    ))}
                    <span className="font-mono text-[9px] text-ink-4">
                      simple ratio{' '}
                      <span className="tabular text-ink-2">{row.simple_density.toFixed(3)}</span>
                    </span>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </ScanPanel>
    </div>
  );
}
