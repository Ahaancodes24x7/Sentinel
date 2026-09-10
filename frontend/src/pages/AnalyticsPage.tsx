import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Activity, MapPinned, TriangleAlert } from 'lucide-react';
import { Chip, Counter, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useTrends } from '../api/hooks';
import { cn } from '../lib/cn';
import { ALL_SITES, useSelectedSite } from '../lib/siteContext';

/**
 * SPC view. The chart draws the CUSUM statistic against its decision interval,
 * because the honest version of "early warning" is a control chart with a
 * stated threshold — not a model output labelled "risk".
 */
export function AnalyticsPage() {
  const { selectedSite } = useSelectedSite();
  const siteParam = selectedSite.site_id !== ALL_SITES.site_id ? selectedSite.site_id : undefined;
  const [granularity, setGranularity] = useState<'weekly' | 'monthly'>('weekly');
  const { data, isLoading, error } = useTrends(siteParam, undefined, granularity);

  const series = data?.series ?? [];
  const alerts = data?.alerts ?? [];
  const cusum = data?.cusum ?? {};
  const upper = cusum.upper ?? [];
  const threshold = cusum.threshold ?? 0;

  const maxCount = Math.max(...series.map((s) => s.count), 1);
  const maxCusum = Math.max(...upper, threshold, 1);
  const alertPeriods = new Set(alerts.map((a) => a.period));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="info" size={6} />
            <span className="font-mono text-2xs tracked text-ink-4">
              REQUIREMENT (F) · TEMPORAL EARLY WARNING
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">Trends &amp; SPC</h1>
        </div>

        <div className="flex gap-2">
          <Link
            to="/operations-map"
            className="flex items-center gap-1.5 rounded-md border border-line-bright px-2.5 py-1.5 font-mono text-2xs tracked text-ink-2 transition-colors hover:border-hivis-edge hover:text-hivis"
            title="Site is set from the Operations Map / site selector — change it there."
          >
            <MapPinned className="h-3 w-3" strokeWidth={2.2} />
            {siteParam ? selectedSite.canonical_name.toUpperCase() : 'ALL SITES'}
          </Link>
          <div className="flex rounded-md border border-line bg-surface-2 p-0.5">
            {(['weekly', 'monthly'] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={cn(
                  'rounded-sm px-3 py-1 font-mono text-2xs tracked transition-colors',
                  granularity === g ? 'bg-surface-hi text-ink' : 'text-ink-3 hover:text-ink',
                )}
              >
                {g.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* The honesty statement, rendered adjacent to the chart, not in a tooltip */}
      {data?.method_note && (
        <div className="flex items-start gap-2 rounded-panel border border-info-edge bg-info-wash px-4 py-2.5">
          <Activity className="mt-0.5 h-3.5 w-3.5 shrink-0 text-info" strokeWidth={2} />
          <p className="text-xs text-ink-2">{data.method_note}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="PERIODS" value={series.length} />
        <Tile label="SPC SIGNALS" value={alerts.length} tone="critical" />
        <Tile
          label="BASELINE MEAN"
          value={Number((cusum.baseline_mean ?? 0).toFixed(1))}
          decimals={1}
        />
        <Tile label="DECISION INTERVAL" value={Number(threshold.toFixed(1))} decimals={1} />
      </div>

      <ScanPanel>
        <PanelHead
          title={`PRECURSOR COUNT · ${granularity.toUpperCase()}`}
          sub="Red columns are periods where the control chart signalled"
          tone="critical"
        />
        {isLoading ? (
          <PanelLoading rows={4} />
        ) : error ? (
          <QueryError error={error} />
        ) : series.length === 0 ? (
          <EmptyPanel title="No time series available" />
        ) : (
          <div className="p-4">
            <div className="flex h-48 items-end gap-[2px]">
              {series.map((point, i) => {
                const flagged = alertPeriods.has(point.period);
                return (
                  <motion.div
                    key={point.period}
                    className="group relative min-w-[3px] flex-1"
                    initial={{ height: 0 }}
                    animate={{ height: `${(point.count / maxCount) * 100}%` }}
                    transition={{ delay: Math.min(i * 0.008, 0.5), duration: 0.5 }}
                    title={`${point.period} · ${point.count} precursors of ${point.total_reports} reports (${(point.precursor_rate * 100).toFixed(0)}%)`}
                  >
                    <div
                      className={cn(
                        'h-full w-full rounded-t-[2px]',
                        flagged ? 'bg-critical' : 'bg-hivis/50 group-hover:bg-hivis',
                      )}
                    />
                  </motion.div>
                );
              })}
            </div>
            <div className="mt-1.5 flex justify-between font-mono text-2xs text-ink-4">
              <span>{series[0]?.period}</span>
              <span>{series[series.length - 1]?.period}</span>
            </div>
          </div>
        )}
      </ScanPanel>

      {/* CUSUM statistic against its decision interval */}
      {upper.length > 0 && (
        <ScanPanel>
          <PanelHead
            title="CUSUM STATISTIC"
            sub={`Cumulative deviation above baseline · signals when it crosses ${threshold.toFixed(1)}`}
            tone="info"
          />
          <div className="p-4">
            <div className="relative h-32">
              {/* threshold line */}
              <div
                className="absolute left-0 right-0 border-t border-dashed border-critical"
                style={{ bottom: `${(threshold / maxCusum) * 100}%` }}
              >
                <span className="absolute -top-4 right-0 font-mono text-2xs text-critical">
                  h = {threshold.toFixed(1)}
                </span>
              </div>
              <div className="flex h-full items-end gap-[2px]">
                {upper.map((v, i) => (
                  <motion.div
                    key={i}
                    className="min-w-[3px] flex-1"
                    initial={{ height: 0 }}
                    animate={{ height: `${(v / maxCusum) * 100}%` }}
                    transition={{ delay: Math.min(i * 0.008, 0.5), duration: 0.4 }}
                  >
                    <div
                      className={cn(
                        'h-full w-full rounded-t-[1px]',
                        v > threshold ? 'bg-critical' : 'bg-info/45',
                      )}
                    />
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </ScanPanel>
      )}

      <ScanPanel>
        <PanelHead
          title="RAISED SIGNALS"
          tone="critical"
          right={<Chip tone={alerts.length ? 'critical' : 'low'}>{alerts.length}</Chip>}
        />
        {alerts.length === 0 ? (
          <EmptyPanel title="Process in control" message="No unusual increases detected." />
        ) : (
          <div className="divide-y divide-line-faint">
            {alerts.map((alert, i) => (
              <motion.div
                key={`${alert.period}-${alert.method}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 px-4 py-3"
              >
                <TriangleAlert
                  className={cn(
                    'mt-0.5 h-4 w-4 shrink-0',
                    alert.severity === 'high' ? 'text-critical' : 'text-high',
                  )}
                  strokeWidth={2}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs tabular text-ink">{alert.period}</span>
                    <Chip tone="info">{alert.method}</Chip>
                    <Chip tone={alert.severity === 'high' ? 'critical' : 'high'}>
                      {alert.severity.toUpperCase()}
                    </Chip>
                  </div>
                  <p className="mt-1 text-sm text-ink-2">{alert.message}</p>
                  <div className="mt-0.5 font-mono text-2xs text-ink-4">
                    observed {alert.count.toFixed(0)} · baseline{' '}
                    {alert.baseline_mean.toFixed(1)} · threshold {alert.threshold.toFixed(1)}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </ScanPanel>
    </div>
  );
}

function Tile({
  label,
  value,
  tone = 'hivis',
  decimals = 0,
}: {
  label: string;
  value: number;
  tone?: 'hivis' | 'critical';
  decimals?: number;
}) {
  return (
    <ScanPanel className="p-3">
      <div className="font-mono text-[9px] tracked text-ink-4">{label}</div>
      <div
        className={cn(
          'mt-1 font-display text-3xl',
          tone === 'critical' ? 'text-critical' : 'text-ink',
        )}
      >
        <Counter value={value} decimals={decimals} />
      </div>
    </ScanPanel>
  );
}
