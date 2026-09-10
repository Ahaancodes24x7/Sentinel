/**
 * Operations Map — an interactive Leaflet/OpenStreetMap layer over the three
 * real OIL India demonstration locations (Duliajan, Digboi, Moran).
 *
 * This is a navigation surface, not a decoration: clicking a marker sets
 * `selectedSite` in the shared site context (lib/siteContext.tsx), the same
 * state the topbar selector and Live Safety Vision read from. Every stat
 * shown in a marker's popover — report count, SIF-potential count, review
 * queue count — comes from a live request against the existing report/site
 * endpoints; nothing here is fabricated.
 *
 * Site LOCATIONS are real public geographic references. The reports, SIF
 * counts and camera feeds attached to them are synthetic demonstration
 * data — see DemoDataNotice below and the banner already shown on every
 * console screen.
 */
import { useMemo } from 'react';
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';
import L from 'leaflet';
import { AlertTriangle, MapPin } from 'lucide-react';
import { Chip } from '../kinetic';
import { useReviewQueue, useSiteDetail, useSites } from '../../api/hooks';
import { REAL_DEMO_SITES, useSelectedSite } from '../../lib/siteContext';
import type { SiteSummaryItem } from '../../api/types';

// Upper Assam, roughly centred between the three sites.
const MAP_CENTER: [number, number] = [27.3, 95.28];

function markerIcon(active: boolean) {
  return L.divIcon({
    className: '',
    html: `<span class="sentinel-map-marker${active ? ' active' : ''}"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -8],
  });
}

function SitePopupContent({ site, onOpenDashboard }: { site: SiteSummaryItem; onOpenDashboard: () => void }) {
  const { data: detail, isLoading } = useSiteDetail(site.site_id);
  const { data: queue } = useReviewQueue(site.site_id, 'oldest', 1);

  return (
    <div className="w-60 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-display text-lg text-ink">{site.canonical_name}</span>
        <Chip tone="medium">DEMO SITE</Chip>
      </div>
      <div className="mt-0.5 font-mono text-2xs tracked text-ink-4">
        {site.region} · {site.state}
      </div>

      {isLoading ? (
        <div className="mt-3 font-mono text-2xs tracked text-ink-4">LOADING…</div>
      ) : (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <PopoverStat label="REPORTS" value={detail?.total_reports ?? 0} />
          <PopoverStat label="SIF" value={detail?.sif_precursor_count ?? 0} tone="text-critical" />
          <PopoverStat label="REVIEW" value={queue?.total ?? 0} tone="text-high" />
        </div>
      )}

      <button
        type="button"
        onClick={onOpenDashboard}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-sm border border-hivis-edge bg-hivis-wash px-2 py-1.5 font-mono text-2xs tracked text-hivis transition-colors hover:bg-hivis hover:text-on-hivis"
      >
        VIEW SITE INTELLIGENCE
      </button>
    </div>
  );
}

function PopoverStat({ label, value, tone = 'text-ink' }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-sm border border-line bg-surface-3 px-1.5 py-1.5 text-center">
      <div className={`font-mono text-sm tabular ${tone}`}>{value}</div>
      <div className="mt-0.5 font-mono text-[8px] tracked text-ink-4">{label}</div>
    </div>
  );
}

export function DemoDataNotice({ className }: { className?: string }) {
  return (
    <div
      className={`flex items-center gap-1.5 font-mono text-2xs tracked text-medium ${className ?? ''}`}
    >
      <AlertTriangle className="h-3 w-3 shrink-0" strokeWidth={2.2} />
      DEMONSTRATION DATA — NOT LIVE OIL DATA
    </div>
  );
}

export function OperationsMap({
  interactive = true,
  height = 440,
  className,
  onSiteOpen,
}: {
  /** Landing-page preview passes false: no zoom/drag, just the three markers. */
  interactive?: boolean;
  height?: number;
  className?: string;
  /** Called (with the site_id) after a marker's "VIEW SITE INTELLIGENCE" is clicked. */
  onSiteOpen?: (siteId: string) => void;
}) {
  const { selectedSite, setSelectedSiteId } = useSelectedSite();
  // The landing-page preview (interactive=false) is unauthenticated and
  // would only get a 401 from this endpoint — it already has the three
  // sites' real coordinates baked in via REAL_DEMO_SITES.
  const { data: sitesData } = useSites(interactive);

  const sites = useMemo<SiteSummaryItem[]>(() => {
    const byId = new Map((sitesData?.sites ?? []).map((s) => [s.site_id, s]));
    // Fall back to the known real coordinates baked into siteContext.tsx so
    // markers render at their correct locations immediately — including on
    // the unauthenticated landing page, which can never load /sites (it
    // requires a session). The richer region/state/description fields fill
    // in once /sites resolves for a signed-in viewer.
    return REAL_DEMO_SITES.map(
      (s) =>
        byId.get(s.site_id) ?? {
          site_id: s.site_id,
          canonical_name: s.canonical_name,
          region: '',
          state: '',
          facility_type: '',
          latitude: s.latitude ?? MAP_CENTER[0],
          longitude: s.longitude ?? MAP_CENTER[1],
          is_synthetic_prototype: false,
          description: '',
          demonstration_notice: 'PUBLIC OIL ASSET',
        },
    );
  }, [sitesData]);

  return (
    <div className={className}>
      <MapContainer
        center={MAP_CENTER}
        zoom={interactive ? 9 : 8}
        scrollWheelZoom={interactive}
        dragging={interactive}
        zoomControl={interactive}
        doubleClickZoom={interactive}
        touchZoom={interactive}
        boxZoom={interactive}
        keyboard={interactive}
        attributionControl={interactive}
        style={{ height, width: '100%', borderRadius: 'var(--radius-panel)' }}
        className="sentinel-leaflet"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
          maxZoom={17}
        />
        {sites.map((site) => (
          <Marker
            key={site.site_id}
            position={[site.latitude, site.longitude]}
            icon={markerIcon(site.site_id === selectedSite.site_id)}
            eventHandlers={interactive ? { click: () => setSelectedSiteId(site.site_id) } : undefined}
          >
            {interactive && (
              <Popup>
                <SitePopupContent
                  site={site}
                  onOpenDashboard={() => {
                    setSelectedSiteId(site.site_id);
                    onSiteOpen?.(site.site_id);
                  }}
                />
              </Popup>
            )}
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

/** Compact legend row — site name + a coloured dot, for panels next to the map. */
export function SiteLegend({ className }: { className?: string }) {
  const { selectedSite, setSelectedSiteId, sites } = useSelectedSite();
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
      {sites.map((s) => (
        <button
          key={s.site_id}
          type="button"
          onClick={() => setSelectedSiteId(s.site_id)}
          className={
            s.site_id === selectedSite.site_id
              ? 'flex items-center gap-1.5 rounded-sm border border-hivis-edge bg-hivis-wash px-2 py-1 font-mono text-2xs tracked text-hivis'
              : 'flex items-center gap-1.5 rounded-sm border border-line-bright px-2 py-1 font-mono text-2xs tracked text-ink-2 transition-colors hover:text-hivis'
          }
        >
          <MapPin className="h-3 w-3" strokeWidth={2.2} />
          {s.canonical_name.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
