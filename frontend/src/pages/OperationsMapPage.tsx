import { useNavigate } from 'react-router-dom';
import { ArrowRight, MapPinned, ShieldAlert } from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { DemoDataNotice, OperationsMap } from '../components/map/OperationsMap';
import { useClusters, useReviewQueue, useSiteDetail, useSummary } from '../api/hooks';
import { ALL_SITES, REAL_DEMO_SITES, useSelectedSite, useSiteUrlSync } from '../lib/siteContext';

/* --------------------------------------------------------------------------
 * Operations Map — turns the three real OIL India demonstration locations
 * (Duliajan, Digboi, Moran) into a site-navigation layer for Sentinel.
 *
 * Locations are real public geographic references. Everything shown about
 * them — reports, SIF-potential counts, review queue depth, clusters and
 * camera feeds — is synthetic demonstration data computed from Sentinel's
 * own report dataset, never fabricated for this screen.
 * ----------------------------------------------------------------------- */

function AllSitesOverview() {
  const { setSelectedSiteId } = useSelectedSite();
  const { data: summary, isLoading } = useSummary();

  return (
    <ScanPanel className="flex h-full flex-col">
      <PanelHead
        title="ALL SITES"
        sub="3 demonstration locations · Assam, India"
        right={<Chip tone="neutral">CROSS-SITE VIEW</Chip>}
      />
      <div className="space-y-4 p-4">
        {isLoading ? (
          <PanelLoading rows={3} />
        ) : (
          <div className="grid grid-cols-3 gap-2">
            <MiniStat label="REPORTS" value={summary?.total_reports ?? 0} />
            <MiniStat label="SIF FLAGGED" value={summary?.sif_flagged_count ?? 0} tone="text-critical" />
            <MiniStat label="PENDING REVIEW" value={summary?.reports_pending_review ?? 0} tone="text-high" />
          </div>
        )}

        <div>
          <div className="font-mono text-[9px] tracked text-ink-4">DEMONSTRATION SITES</div>
          <div className="mt-2 space-y-1.5">
            {REAL_DEMO_SITES.map((s) => (
              <button
                key={s.site_id}
                type="button"
                onClick={() => setSelectedSiteId(s.site_id)}
                className="flex w-full items-center justify-between rounded-md border border-line px-3 py-2 text-left transition-colors hover:border-hivis-edge hover:bg-hivis-wash/40"
              >
                <span className="flex items-center gap-2">
                  <MapPinned className="h-3.5 w-3.5 text-hivis" strokeWidth={2} />
                  <span className="text-sm text-ink">{s.canonical_name}</span>
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-ink-4" strokeWidth={2} />
              </button>
            ))}
          </div>
        </div>

        <p className="border-t border-line pt-3 text-xs text-ink-4">
          Select a demonstration site on the map or above to view site-specific safety
          intelligence.
        </p>
      </div>
    </ScanPanel>
  );
}

function SiteIntelligencePanel() {
  const navigate = useNavigate();
  const { selectedSite } = useSelectedSite();
  const { data: detail, isLoading, error } = useSiteDetail(selectedSite.site_id);
  const { data: queue } = useReviewQueue(selectedSite.site_id, 'oldest', 1);
  const { data: clustersData } = useClusters(selectedSite.site_id, 2);

  const topCluster = [...(clustersData?.clusters ?? [])].sort(
    (a, b) => b.member_count - a.member_count,
  )[0];
  const topLsr = detail?.top_lsrs?.[0];

  if (isLoading) {
    return (
      <ScanPanel className="flex h-full flex-col">
        <PanelHead title={selectedSite.canonical_name.toUpperCase()} />
        <PanelLoading rows={6} />
      </ScanPanel>
    );
  }

  if (error || !detail) {
    return (
      <ScanPanel className="flex h-full flex-col">
        <PanelHead title={selectedSite.canonical_name.toUpperCase()} />
        <QueryError error={error} compact />
      </ScanPanel>
    );
  }

  return (
    <ScanPanel className="flex h-full flex-col">
      <PanelHead
        title={detail.site.toUpperCase()}
        sub={`${detail.region} · ${detail.state}`}
        right={<Chip tone="medium">DEMONSTRATION SITE</Chip>}
      />
      <div className="flex-1 space-y-4 p-4">
        <div className="grid grid-cols-3 gap-2">
          <MiniStat label="REPORTS" value={detail.total_reports} />
          <MiniStat label="SIF POTENTIAL" value={detail.sif_precursor_count} tone="text-critical" />
          <MiniStat label="REVIEW QUEUE" value={queue?.total ?? 0} tone="text-high" />
        </div>

        <div>
          <div className="flex justify-between font-mono text-2xs text-ink-4">
            <span>PRECURSOR DENSITY</span>
            <span className="tabular text-ink-2">{(detail.precursor_density * 100).toFixed(1)}%</span>
          </div>
          <Bar value={detail.precursor_density} tone="hivis" className="mt-1" />
          <p className="mt-1 text-[10px] text-ink-4">{detail.density_formula}</p>
        </div>

        <div>
          <div className="font-mono text-[9px] tracked text-ink-4">TOP LIFE-SAVING RULE</div>
          {topLsr ? (
            <div className="mt-1.5 flex items-center gap-2">
              <Chip tone="hivis">{topLsr.lsr}</Chip>
              <span className="font-mono text-2xs text-ink-4">{topLsr.count} flagged reports</span>
            </div>
          ) : (
            <p className="mt-1 text-xs text-ink-4">No SIF-flagged reports yet at this site.</p>
          )}
        </div>

        <div>
          <div className="font-mono text-[9px] tracked text-ink-4">TOP PRECURSOR PATTERN</div>
          {topCluster ? (
            <div className="mt-1.5 rounded-md border border-line bg-surface-2 p-2.5">
              <div className="flex items-center gap-1.5">
                <ShieldAlert className="h-3 w-3 text-high" strokeWidth={2.2} />
                <span className="font-mono text-2xs tracked text-ink-3">
                  {topCluster.member_count} reports · {topCluster.primary_lsr}
                </span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-ink-2">{topCluster.pattern_summary}</p>
            </div>
          ) : (
            <p className="mt-1 text-xs text-ink-4">No recurring pattern clustered at this site yet.</p>
          )}
        </div>
      </div>

      <div className="border-t border-line p-3">
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-hivis px-3 py-2 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.01]"
        >
          VIEW SITE INTELLIGENCE <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.4} />
        </button>
      </div>
    </ScanPanel>
  );
}

export function OperationsMapPage() {
  useSiteUrlSync();
  const { selectedSite } = useSelectedSite();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="hivis" size={6} />
            <span className="font-mono text-2xs tracked text-ink-4">SITE NAVIGATION</span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">Operations Map</h1>
          <p className="mt-1.5 max-w-2xl text-sm text-ink-3">
            Select a demonstration site to view site-specific safety intelligence.
          </p>
        </div>
        <DemoDataNotice />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.6fr_1fr]">
        <ScanPanel className="overflow-hidden p-2">
          <OperationsMap height={480} />
        </ScanPanel>

        {selectedSite.site_id === ALL_SITES.site_id ? <AllSitesOverview /> : <SiteIntelligencePanel />}
      </div>

      <p className="text-xs text-ink-4">
        Site locations are real geographic references publicly associated with OIL India Limited.
        Safety observations, precursor clusters, trends and camera feeds shown for them are
        synthetic demonstration data generated for this prototype — not real-time OIL incidents or
        live OIL cameras.
      </p>
    </div>
  );
}

function MiniStat({ label, value, tone = 'text-ink' }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 px-2 py-2 text-center">
      <div className={`font-display text-2xl ${tone}`}>
        <Counter value={value} />
      </div>
      <div className="mt-0.5 font-mono text-[8px] tracked text-ink-4">{label}</div>
    </div>
  );
}
