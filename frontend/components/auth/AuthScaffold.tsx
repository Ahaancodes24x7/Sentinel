import type { ReactNode } from "react";
import Link from "next/link";

/**
 * Two-pane auth shell shared by /login and /signup: a steel brand rail on the
 * left (desktop), the form card on the right. Same permit-form vernacular as
 * the console.
 */
export function AuthScaffold({
  heading,
  intro,
  children,
  footer,
}: {
  heading: string;
  intro?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <main className="grid min-h-screen bg-panel md:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden flex-col gap-12 overflow-hidden border-r border-line bg-steel p-10 text-steel-fg md:flex">
        <div className="hazard-stripe absolute inset-x-0 top-0 h-1" aria-hidden />
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-lg font-bold uppercase tracking-[0.16em]">
            Sentinel
          </span>
          <span className="text-2xs uppercase tracking-[0.14em] text-steel-fg/60">
            SIF Precursor Monitor
          </span>
        </Link>

        <div className="space-y-4">
          <p className="text-lg font-semibold leading-snug">
            Serious-injury precursors, pulled from the near-miss reports you
            already collect.
          </p>
          <p className="text-sm text-steel-fg/70">
            Extraction, ontology reasoning, calibrated classification and a human
            review loop — one console for the HSE team.
          </p>
        </div>

        <p className="mt-auto text-2xs text-steel-fg/50">
          Demo build · synthetic dataset unless connected to a live backend.
        </p>
      </aside>

      <section className="flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-md">
          <div className="mb-6 md:hidden">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-xl font-bold uppercase tracking-[0.16em] text-ink">
                Sentinel
              </span>
              <span className="label">SIF Precursor Monitor</span>
            </Link>
          </div>

          <h1 className="text-xl font-bold tracking-tight text-ink">{heading}</h1>
          {intro ? <p className="mt-2 text-sm text-muted">{intro}</p> : null}

          <div className="mt-6">{children}</div>

          {footer ? (
            <div className="mt-6 border-t border-line pt-4 text-sm text-muted">
              {footer}
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
