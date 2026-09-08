"use client";

import Link from "next/link";
import { useAuth } from "@/lib/api/auth-store";
import { NAV_LINKS } from "./content";

/**
 * Top bar for the public landing page. Swaps the primary action to "Open
 * console" once a session exists, so a signed-in visitor isn't sent back
 * through sign-in.
 */
export function LandingHeader() {
  const { session, ready } = useAuth();
  const authed = ready && !!session;

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-panel">
      <div className="mx-auto flex max-w-[1100px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-sm font-bold uppercase tracking-[0.16em] text-ink">
            Sentinel
          </span>
          <span className="hidden text-2xs uppercase tracking-[0.14em] text-muted sm:inline">
            SIF Precursor Monitor
          </span>
        </Link>

        <nav className="hidden items-center gap-5 md:flex" aria-label="Page sections">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-xs font-semibold uppercase tracking-[0.06em] text-muted hover:text-ink"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {authed ? (
            <Link
              href="/reports"
              className="bg-steel px-4 py-2 text-xs font-semibold uppercase tracking-[0.06em] text-steel-fg hover:opacity-90"
            >
              Open console
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden px-3 py-2 text-xs font-semibold uppercase tracking-[0.06em] text-muted hover:text-ink sm:inline"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="bg-steel px-4 py-2 text-xs font-semibold uppercase tracking-[0.06em] text-steel-fg hover:opacity-90"
              >
                Request access
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
