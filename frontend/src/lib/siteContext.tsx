/**
 * Global site selector — the ONE source of truth for "which site am I
 * looking at right now."
 *
 * The demo spans three real OIL India locations (Duliajan, Digboi, Moran),
 * chosen on the Operations Map, the topbar selector, or a report/site link,
 * and everywhere else in the console — Reports, the dashboard, patterns,
 * barrier failures, trends and Live Safety Vision's camera list — reads from
 * this same selection rather than keeping its own copy of it. Selecting
 * "ALL SITES" clears the filter and restores the global, cross-site view.
 *
 * Site locations (Duliajan/Digboi/Moran and their coordinates) are real
 * geographic references. The reports, clusters, trends and camera feeds
 * filtered by them are synthetic demonstration data — see the
 * "DEMONSTRATION DATA" notice shown alongside the selector and the map.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';

export interface DemoSite {
  site_id: string;
  canonical_name: string;
  /** Real public coordinates — mirrors the backend site registry. Kept here
   * too (not just fetched from GET /sites) so the Operations Map preview on
   * the unauthenticated landing page, which cannot call an authenticated
   * API, can still place its three markers at their real locations instead
   * of collapsing them onto a single fallback point. */
  latitude?: number;
  longitude?: number;
}

/** The three real OIL India demonstration locations — used for the
 * Operations Map markers and Live Safety Vision's per-site camera list.
 * Does NOT include the "ALL SITES" pseudo-entry (see SITE_SELECTOR_OPTIONS). */
export const REAL_DEMO_SITES: DemoSite[] = [
  { site_id: 'duliajan', canonical_name: 'Duliajan', latitude: 27.3587, longitude: 95.3197 },
  { site_id: 'digboi', canonical_name: 'Digboi', latitude: 27.38, longitude: 95.63 },
  { site_id: 'moran', canonical_name: 'Moran', latitude: 27.1856, longitude: 94.9297 },
];

/** Pseudo-site restoring the unfiltered, cross-site view. `qs()` in
 * api/client.ts already drops a `site=all` param, so passing this id
 * straight into a report/site-scoped query string is filter-free by
 * construction — no special-casing needed at each call site. */
export const ALL_SITES: DemoSite = { site_id: 'all', canonical_name: 'All Sites' };

export const SITE_SELECTOR_OPTIONS: DemoSite[] = [ALL_SITES, ...REAL_DEMO_SITES];

const STORAGE_KEY = 'sentinel_selected_site';

interface SiteContextValue {
  selectedSite: DemoSite;
  setSelectedSiteId: (siteId: string) => void;
  /** ALL SITES + the three real demo sites, for the site selector control. */
  sites: DemoSite[];
}

const SiteContext = createContext<SiteContextValue | null>(null);

export function SiteProvider({ children }: { children: ReactNode }) {
  const [siteId, setSiteId] = useState<string>(() => {
    if (typeof window === 'undefined') return ALL_SITES.site_id;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored && SITE_SELECTOR_OPTIONS.some((s) => s.site_id === stored)
      ? stored
      : ALL_SITES.site_id;
  });

  useEffect(() => {
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, siteId);
  }, [siteId]);

  const selectedSite = SITE_SELECTOR_OPTIONS.find((s) => s.site_id === siteId) ?? ALL_SITES;

  return (
    <SiteContext.Provider
      value={{ selectedSite, setSelectedSiteId: setSiteId, sites: SITE_SELECTOR_OPTIONS }}
    >
      {children}
    </SiteContext.Provider>
  );
}

export function useSelectedSite(): SiteContextValue {
  const ctx = useContext(SiteContext);
  if (!ctx) throw new Error('useSelectedSite must be used within a SiteProvider');
  return ctx;
}

/**
 * Keeps `?site=` in the current page's URL in sync with the shared selector,
 * so a link like `/dashboard?site=DULIAJAN` opens straight into that site's
 * view (and switching sites in-app updates the address bar to match) without
 * disturbing any other query params or breaking existing routes. Call this
 * once, from a page that wants its site scoping to be shareable — currently
 * the Operations Map and the dashboard, matching the two example URLs this
 * is built for.
 */
export function useSiteUrlSync() {
  const { selectedSite, setSelectedSiteId, sites } = useSelectedSite();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSite = searchParams.get('site');

  // URL -> state: a shared/bookmarked link picks the site on load.
  useEffect(() => {
    if (!urlSite) return;
    const match = sites.find(
      (s) =>
        s.site_id.toLowerCase() === urlSite.toLowerCase() ||
        s.canonical_name.toLowerCase() === urlSite.toLowerCase(),
    );
    if (match && match.site_id !== selectedSite.site_id) {
      setSelectedSiteId(match.site_id);
    }
    // Only react to the URL changing (e.g. following a new link), not to
    // every selection change — the effect below handles that direction.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSite]);

  // state -> URL: switching sites in-app keeps the address bar shareable.
  useEffect(() => {
    const desired = selectedSite.site_id.toUpperCase();
    if ((urlSite ?? '').toUpperCase() === desired) return;
    const next = new URLSearchParams(searchParams);
    next.set('site', desired);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSite.site_id]);
}
