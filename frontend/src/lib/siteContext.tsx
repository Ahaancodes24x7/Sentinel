/**
 * Global site selector.
 *
 * The demo now spans three real OIL India locations (Duliajan, Digboi,
 * Moran) rather than one. This context holds which one is "active" right
 * now, persisted across reloads, so Live Safety Vision (and anything else
 * that wants to follow it) can react to the switch without every page
 * needing its own copy of the same three-item list.
 *
 * This does not replace the per-page site FILTERS already on Reports / Site
 * Risk / Patterns — those stay local and can filter across every site in the
 * full registry (real assets and synthetic prototypes alike). This is the
 * "which real site am I looking at right now" selector for the parts of the
 * product built around the three-site demo narrative.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export interface DemoSite {
  site_id: string;
  canonical_name: string;
}

export const REAL_DEMO_SITES: DemoSite[] = [
  { site_id: 'duliajan', canonical_name: 'Duliajan' },
  { site_id: 'digboi', canonical_name: 'Digboi' },
  { site_id: 'moran', canonical_name: 'Moran' },
];

const STORAGE_KEY = 'sentinel_selected_site';

interface SiteContextValue {
  selectedSite: DemoSite;
  setSelectedSiteId: (siteId: string) => void;
  sites: DemoSite[];
}

const SiteContext = createContext<SiteContextValue | null>(null);

export function SiteProvider({ children }: { children: ReactNode }) {
  const [siteId, setSiteId] = useState<string>(() => {
    if (typeof window === 'undefined') return REAL_DEMO_SITES[0].site_id;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored && REAL_DEMO_SITES.some((s) => s.site_id === stored)
      ? stored
      : REAL_DEMO_SITES[0].site_id;
  });

  useEffect(() => {
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, siteId);
  }, [siteId]);

  const selectedSite = REAL_DEMO_SITES.find((s) => s.site_id === siteId) ?? REAL_DEMO_SITES[0];

  return (
    <SiteContext.Provider value={{ selectedSite, setSelectedSiteId: setSiteId, sites: REAL_DEMO_SITES }}>
      {children}
    </SiteContext.Provider>
  );
}

export function useSelectedSite(): SiteContextValue {
  const ctx = useContext(SiteContext);
  if (!ctx) throw new Error('useSelectedSite must be used within a SiteProvider');
  return ctx;
}
