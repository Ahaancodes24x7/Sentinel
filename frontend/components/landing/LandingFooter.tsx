import { FOOTER_NOTE } from "./content";

export function LandingFooter() {
  return (
    <footer className="border-t border-line bg-panel">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-3 px-4 py-8 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold uppercase tracking-[0.16em] text-ink">
            Sentinel
          </span>
          <span className="label">SIF Precursor Monitor</span>
        </div>
        <p className="max-w-xl text-2xs text-muted">{FOOTER_NOTE}</p>
      </div>
    </footer>
  );
}
