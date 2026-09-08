"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/api/auth-store";
import { USE_MOCKS } from "@/lib/api/client";
import { Nav } from "./Nav";
import { RoleChip } from "./RoleChip";

/**
 * The authed application chrome: steel top bar, role-driven left nav, and a
 * slot for a per-screen data banner (e.g. the synthetic-data banner).
 */
export function AppShell({
  children,
  banner,
}: {
  children: ReactNode;
  banner?: ReactNode;
}) {
  const { session, ready } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  if (!ready) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted">
        Loading…
      </div>
    );
  }
  if (!session) return null; // AuthProvider redirects to /login

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 flex items-center justify-between gap-2 bg-steel px-3 py-2 text-steel-fg sm:px-4">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <button
            type="button"
            className="border border-steel-fg/40 px-2 py-1 text-xs md:hidden"
            aria-expanded={navOpen}
            aria-controls="primary-nav"
            onClick={() => setNavOpen((v) => !v)}
          >
            Menu
          </button>
          <Link href="/reports" className="flex items-baseline gap-2">
            <span className="text-sm font-bold uppercase tracking-[0.14em]">
              Sentinel
            </span>
            <span className="hidden text-2xs uppercase tracking-[0.14em] text-steel-fg/60 sm:inline">
              SIF Precursor Monitor
            </span>
          </Link>
          {USE_MOCKS && (
            <span className="hidden shrink-0 whitespace-nowrap border border-caution px-1.5 py-[2px] text-[0.5625rem] uppercase tracking-[0.06em] text-caution sm:inline-block">
              Offline demo
            </span>
          )}
        </div>
        <RoleChip />
      </header>

      <div className="mx-auto flex max-w-[1400px]">
        <aside
          id="primary-nav"
          className={`${
            navOpen ? "block" : "hidden"
          } w-full shrink-0 border-b border-line bg-panel md:block md:w-52 md:border-b-0 md:border-r`}
        >
          <div className="label px-3 py-2">Navigation</div>
          <Nav onNavigate={() => setNavOpen(false)} />
        </aside>

        <main className="min-w-0 flex-1">
          {banner}
          <div className="p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
