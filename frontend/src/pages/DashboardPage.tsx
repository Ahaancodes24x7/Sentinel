import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowUpRight, Layers, Siren, TrendingUp } from 'lucide-react';
import {
  Bar,
  Chip,
  Counter,
  LiveFeed,
  PanelHead,
  PulseDot,
  ScanPanel,
  Stagger,
  StaggerItem,
  type Tone,
} from '../components/kinetic';
import { Hint, HelpDot, HINTS } from '../components/common/Hint';
import { EmptyPanel, NoDataYet, PanelLoading, QueryError } from '../components/common/QueryState';
import {
  useClusters,
  useRankings,
  useReviewQueue,
  useSiteDetail,
  useSummary,
  useTrends,
} from '../api/hooks';
import { BUCKET_META, type Bucket } from '../api/types';
import { cn } from '../lib/cn';
import { ALL_SITES, useSelectedSite, useSiteUrlSync } from '../lib/siteContext';
import { DemoDataNotice } from '../components/map/OperationsMap';

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

/* --------------------------------------------------------------------------
 * This screen answers three questions and nothing else:
 *
 *   1. What needs my attention right now?   -> priority stream
 *   2. Where is the risk concentrated?      -> site ranking
 *   3. Is anything getting worse?           -> trend chart
 *
 * The confidence-routing breakdown and the intervention list used to live here
 * too. Both were removed: routing belongs on the Review Queue where you act on
 * it, and interventions have a screen of their own. Repeating them here turned
 * the landing page into a wall of panels with no obvious entry point.
 * ----------------------------------------------------------------------- */

function MetricTile({
  label,
  value,
  sub,
  tone = 'hivis',
  icon: Icon,
  hint,
  loading = false,
  to,
}: {
  label: string;
  value: number;
  sub?: string;
  tone?: Tone;
  icon: typeof Siren;
  hint: string;
  loading?: boolean;
  to?: string;
}) {
  const body = (
    <ScanPanel className="h-full p-4 transition-colors hover:border-line-bright">
      <div className="flex items-start justify-between">
        <span className="flex items-center gap-1.5 font-mono text-2xs tracked text-ink-4">
          {label}
          <HelpDot content={hint} />
        </span>
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            tone === 'critical' ? 'text-critical' : tone === 'high' ? 'text-high' : 'text-hivis',
          )}
          strokeWidth={2}
        />
      </div>

      <div className="mt-2 font-display text-4xl text-ink">
        {loading ? <span className="text-ink-4">—</span> : <Counter value={value} />}
      </div>

      <div className="mt-1 text-xs text-ink-3">
        {loading ? <span className="font-mono text-2xs tracked text-ink-4">LOADING…</span> : sub}
      </div>
    </ScanPanel>
  );

  return <StaggerItem>{to ? <Link to={to}>{body}</Link> : body}</StaggerItem>;
}

/* -------------------------------------------------------------------------- */

function PriorityStream({ site }: { site?: string }) {
  const { data, isLoading, error } = useReviewQueue(site, 'newest', 40);
  const items = data?.items ?? [];

  return (
    <ScanPanel className="flex h-full flex-col">
      <PanelHead
        title="NEEDS ATTENTION"
        sub="Newest flagged observations"
        tone="critical"
        right={
          <div className="flex items-center gap-1.5">
            <PulseDot tone="critical" size={6} />
            <span className="font-mono text-2xs tracked text-ink-4">LIVE</span>
          </div>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <PanelLoading rows={6} />
        ) : error ? (
          <QueryError error={error} compact />
        ) : items.length === 0 ? (
          <NoDataYet />
        ) : (
          <LiveFeed
            items={items}
            max={9}
            keyFor={(r) => r.report_id}
            renderItem={(r) => (
              <Link
                to={`/reports/${r.report_id}`}
                className="block px-4 py-2.5 transition-colors hover:bg-surface-2"
              >
                <div className="flex items-center gap-2">
                  <Chip tone={BUCKET_TONE[r.bucket]} dot>
                    {BUCKET_META[r.bucket]?.short ?? r.bucket}
                  </Chip>
                  <span className="truncate font-mono text-2xs text-ink-3">{r.site}</span>
                  <span className="ml-auto font-mono text-2xs tabular text-ink-4">
                    {r.timestamp?.slice(0, 10)}
                  </span>
                </div>
                <div className="mt-1 truncate text-xs text-ink-2">
                  {r.lsr_tag && r.lsr_tag !== 'N/A' ? r.lsr_tag : 'Rule not assigned'}
                </div>
              </Link>
            )}
          />
        )}
      </div>

      <div className="border-t border-line px-4 py-2">
        <Link
          to="/review-queue"
          className="flex items-center gap-1.5 font-mono text-2xs tracked text-hivis hover:underline"
        >
          OPEN REVIEW QUEUE <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </ScanPanel>
  );
}

/* -------------------------------------------------------------------------- */

function SiteRanking() {
  const { data, isLoading, error } = useRankings('composite', 'site');
  const rows = (data?.rankings ?? []).slice(0, 7);
  const max = Math.max(...rows.map((r) => r.density), 0.0001);

  return (
    <ScanPanel className="flex h-full flex-col">
      <PanelHead
        title="WHERE THE RISK IS"
        sub="Ranked by precursor density"
        right={
          <Hint content={HINTS.compositeMetric} side="left">
            <Chip tone="medium">UNCALIBRATED</Chip>
          </Hint>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <PanelLoading rows={6} />
        ) : error ? (
          <QueryError error={error} compact />
        ) : rows.length === 0 ? (
          <EmptyPanel title="No ranked sites" />
        ) : (
          <div className="space-y-2.5">
            {rows.map((row, i) => (
              <motion.div
                key={row.group}
                layout
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04, duration: 0.4 }}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-xs text-ink">{row.group}</span>
                  <div className="flex shrink-0 items-baseline gap-2">
                    <span className="font-mono text-2xs tabular text-ink-3">
                      {row.sif_flagged_count}/{row.total_reports}
                    </span>
                    <span className="font-mono text-sm tabular text-hivis">
                      {row.density.toFixed(2)}
                    </span>
                  </div>
                </div>
                <Bar
                  value={row.density / max}
                  tone={i === 0 ? 'critical' : i < 3 ? 'high' : 'hivis'}
                  delay={i * 0.05}
                  className="mt-1"
                />
                <div className="mt-0.5 flex items-center gap-2 text-2xs text-ink-4">
                  <span className="truncate">{row.primary_lsr}</span>
                  {row.trend_direction !== 'flat' && (
                    <span
                      className={cn(
                        'flex shrink-0 items-center gap-0.5 font-mono',
                        row.trend_direction === 'up' ? 'text-critical' : 'text-low',
                      )}
                    >
                      <ArrowUpRight
                        className={cn('h-2.5 w-2.5', row.trend_direction === 'down' && 'rotate-90')}
                      />
                      {Math.abs(row.trend_pct).toFixed(0)}%
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
      <div className="border-t border-line px-4 py-2">
        <Link
          to="/risk-intelligence"
          className="flex items-center gap-1.5 font-mono text-2xs tracked text-hivis hover:underline"
        >
          COMPARE SITES <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </ScanPanel>
  );
}

/* -------------------------------------------------------------------------- */

/**
 * Replaces the cross-site ranking panel when a single demonstration site is
 * selected — ranking one site against itself is meaningless, so this shows
 * what a site-scoped view actually needs: its own density, top rule and
 * barrier profile, all computed server-side over that site's reports.
 */
function SiteFocus({ siteId, siteName }: { siteId: string; siteName: string }) {
  const { data, isLoading, error } = useSiteDetail(siteId);

  return (
    <ScanPanel className="flex h-full flex-col">
      <PanelHead
        title={`${siteName.toUpperCase()} SITE INTELLIGENCE`}
        sub="Precursor density and barrier profile, this site only"
        right={
          <Link
            to="/operations-map"
            className="font-mono text-2xs tracked text-hivis hover:underline"
          >
            MAP →
          </Link>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <PanelLoading rows={5} />
        ) : error || !data ? (
          <QueryError error={error} compact />
        ) : (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between font-mono text-2xs text-ink-4">
                <span>PRECURSOR DENSITY</span>
                <span className="tabular text-ink-2">
                  {(data.precursor_density * 100).toFixed(1)}%
                </span>
              </div>
              <Bar value={data.precursor_density} tone="hivis" className="mt-1" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(data.barrier_profile).map(([k, v]) => (
                <div key={k} className="rounded-md border border-line bg-surface-2 px-2 py-1.5 text-center">
                  <div className="font-mono text-lg tabular text-ink">{v}</div>
                  <div className="font-mono text-[8px] tracked text-ink-4">
                    {k.replace(/_/g, ' ').toUpperCase()}
                  </div>
                </div>
              ))}
            </div>
            {data.top_lsrs.slice(0, 3).map((l) => (
              <div key={l.lsr} className="flex items-center justify-between gap-2">
                <span className="truncate text-xs text-ink-2">{l.lsr}</span>
                <span className="font-mono text-2xs tabular text-ink-4">{l.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </ScanPanel>
  );
}

/* -------------------------------------------------------------------------- */

function TrendStrip({ site }: { site?: string }) {
  const { data, isLoading, error } = useTrends(site);
  const series = data?.series ?? [];
  const alerts = data?.alerts ?? [];
  const baseline = data?.cusum?.baseline_mean ?? 0;
  const alertPeriods = new Set(alerts.map((a) => a.period));
  const max = Math.max(...series.map((s) => s.count), 1);

  return (
    <ScanPanel className="flex flex-col">
      <PanelHead
        title="IS ANYTHING GETTING WORSE?"
        sub="Weekly precursor count against its own baseline"
        tone="info"
        right={
          <Hint content={HINTS.cusum} side="left">
            {alerts.length > 0 ? (
              <Chip tone="critical" dot>
                {alerts.length} SIGNALS
              </Chip>
            ) : (
              <Chip tone="low">IN CONTROL</Chip>
            )}
          </Hint>
        }
      />

      {isLoading ? (
        <PanelLoading rows={3} />
      ) : error ? (
        <QueryError error={error} compact />
      ) : series.length === 0 ? (
        <EmptyPanel title="No time series yet" />
      ) : (
        <div className="p-4">
          <div className="flex h-32 items-end gap-[3px]">
            {series.slice(-52).map((point, i) => {
              const flagged = alertPeriods.has(point.period);
              return (
                <motion.div
                  key={point.period}
                  className="group relative flex-1"
                  initial={{ height: 0 }}
                  animate={{ height: `${(point.count / max) * 100}%` }}
                  transition={{ delay: i * 0.006, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                  title={`${point.period} · ${point.count} precursors of ${point.total_reports} reports`}
                >
                  <div
                    className={cn(
                      'h-full w-full rounded-t-[2px] transition-opacity',
                      flagged ? 'bg-critical' : 'bg-hivis/55 group-hover:bg-hivis',
                    )}
                  />
                </motion.div>
              );
            })}
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 font-mono text-2xs text-ink-4">
            <span>{series.slice(-52)[0]?.period}</span>
            <span className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-sm bg-hivis/55" /> weekly count
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-sm bg-critical" /> unusual rise
              </span>
              <span>baseline {baseline.toFixed(0)}</span>
            </span>
            <span>{series[series.length - 1]?.period}</span>
          </div>
        </div>
      )}

      <div className="border-t border-line px-4 py-2">
        <Link
          to="/analytics"
          className="flex items-center gap-1.5 font-mono text-2xs tracked text-hivis hover:underline"
        >
          FULL CONTROL CHARTS <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </ScanPanel>
  );
}

/* -------------------------------------------------------------------------- */

export function DashboardPage() {
  useSiteUrlSync();
  const { selectedSite } = useSelectedSite();
  const siteScoped = selectedSite.site_id !== ALL_SITES.site_id;
  const siteParam = siteScoped ? selectedSite.site_id : undefined;

  const { data: summary, isLoading: sLoading, error: sError } = useSummary(siteParam);
  const { data: clusters, isLoading: cLoading } = useClusters(siteParam, 3);

  const emerging = (clusters?.clusters ?? []).filter((c) => c.pattern_type === 'emerging').length;
  const pending = summary?.reports_pending_review ?? 0;

  if (sError) {
    return (
      <div className="mx-auto max-w-2xl pt-16">
        <QueryError error={sError} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Masthead */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="hivis" size={7} />
            <span className="font-mono text-2xs tracked text-ink-4">
              SENTINEL / {siteScoped ? selectedSite.canonical_name.toUpperCase() : 'ALL SITES'} · LIVE
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-5xl text-ink">
            Precursor <span className="text-hivis">Watch</span>
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-ink-3">
            {siteScoped
              ? `Reports describing a situation that could have killed someone at ${selectedSite.canonical_name} — including the ones where nobody was hurt.`
              : 'Reports describing a situation that could have killed someone — including the ones where nobody was hurt.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Hint content="File a new observation and see the engine's verdict immediately.">
            <Link
              to="/submit"
              className="flex items-center gap-2 rounded-md border border-hivis-edge bg-hivis-wash px-3 py-2 font-mono text-2xs tracked text-hivis transition-transform hover:scale-[1.02]"
            >
              <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={2.4} />
              FILE A REPORT
            </Link>
          </Hint>
          <Hint content="Open the queue of reports waiting for a human decision.">
            <Link
              to="/review-queue"
              className="flex items-center gap-2 rounded-md bg-hivis px-3 py-2 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.02]"
            >
              <Siren className="h-3.5 w-3.5" strokeWidth={2.4} />
              TRIAGE {pending > 0 ? `(${pending.toLocaleString()})` : ''}
            </Link>
          </Hint>
        </div>
      </div>

      {siteScoped && <DemoDataNotice />}

      {/* Three metrics, not four */}
      <Stagger className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricTile
          label="REPORTS ANALYSED"
          value={summary?.total_reports ?? 0}
          sub="Whole corpus, end to end"
          icon={Layers}
          tone="hivis"
          hint="Every report that has been through the full pipeline."
          loading={sLoading && !summary}
        />
        <MetricTile
          label="AWAITING REVIEW"
          value={pending}
          sub="A person still has to decide"
          icon={Siren}
          tone="critical"
          hint={HINTS.precursor}
          loading={sLoading && !summary}
          to="/review-queue"
        />
        <MetricTile
          label="RECURRING PATTERNS"
          value={summary?.high_priority_pattern_count ?? 0}
          sub={`${emerging} started recently`}
          icon={TrendingUp}
          tone="high"
          hint={HINTS.cluster}
          loading={(sLoading && !summary) || (cLoading && !clusters)}
          to="/patterns"
        />
      </Stagger>

      {/* Two panels side by side */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <PriorityStream site={siteParam} />
        {siteScoped ? (
          <SiteFocus siteId={selectedSite.site_id} siteName={selectedSite.canonical_name} />
        ) : (
          <SiteRanking />
        )}
      </div>

      {/* One full-width trend */}
      <TrendStrip site={siteParam} />
    </div>
  );
}
