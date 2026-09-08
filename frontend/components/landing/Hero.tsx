import Link from "next/link";
import { HERO } from "./content";

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-panel">
      {/* Barrier-tape motif — reserved for the single highest-severity element on the page. */}
      <div className="hazard-stripe absolute inset-x-0 top-0 h-1" aria-hidden />
      <div className="mx-auto max-w-[1100px] px-4 py-16 sm:px-6 md:py-24">
        <p className="label mb-4">{HERO.kicker}</p>
        <h1 className="max-w-3xl text-xl font-bold leading-tight tracking-tight text-ink sm:text-2xl md:text-[2.55rem] md:leading-[1.12]">
          {HERO.title}
        </h1>
        <p className="mt-5 max-w-2xl text-sm text-muted md:text-base">
          {HERO.body}
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link
            href="/signup"
            className="bg-steel px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg hover:opacity-90"
          >
            Request access
          </Link>
          <Link
            href="/login"
            className="border border-line bg-surface px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.06em] text-ink hover:border-focus"
          >
            Sign in
          </Link>
        </div>
      </div>
    </section>
  );
}
