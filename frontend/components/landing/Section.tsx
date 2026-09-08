import type { ReactNode } from "react";

/**
 * A landing-page section shell: numbered eyebrow, title, optional lede, and a
 * consistent max-width + vertical rhythm. Same permit-form vernacular as the
 * console — hairline rules, uppercase labels, no rounded corners.
 */
export function Section({
  id,
  index,
  eyebrow,
  title,
  lede,
  children,
  className = "",
}: {
  id?: string;
  index: string;
  eyebrow: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={`scroll-mt-16 border-t border-line ${className}`}
    >
      <div className="mx-auto max-w-[1100px] px-4 py-14 sm:px-6 md:py-20">
        <header className="mb-8 flex flex-col gap-3 md:mb-10">
          <div className="flex items-center gap-2">
            <span className="tnum label !text-focus">{index}</span>
            <span className="label">{eyebrow}</span>
          </div>
          <h2 className="max-w-2xl text-xl font-bold tracking-tight text-ink md:text-2xl">
            {title}
          </h2>
          {lede ? (
            <p className="max-w-2xl text-sm text-muted md:text-base">{lede}</p>
          ) : null}
        </header>
        {children}
      </div>
    </section>
  );
}
