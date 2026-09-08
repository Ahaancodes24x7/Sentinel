import type { ReactNode } from "react";

/**
 * A permit-form panel: hairline border, a heavy top rule, uppercase title.
 * No rounded corners, no drop shadow — this is instrumentation, not a card.
 */
export function Panel({
  title,
  aside,
  children,
  className = "",
  tone = "default",
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  tone?: "default" | "danger" | "caution" | "clear";
}) {
  const rule =
    tone === "danger"
      ? "border-t-danger"
      : tone === "caution"
        ? "border-t-caution"
        : tone === "clear"
          ? "border-t-clear"
          : "border-t-steel";

  return (
    <section
      className={`min-w-0 border border-line border-t-2 bg-surface ${rule} ${className}`}
    >
      {(title || aside) && (
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-line px-4 py-2">
          <h2 className="label !text-ink">{title}</h2>
          {aside ? <div className="min-w-0">{aside}</div> : null}
        </header>
      )}
      <div className="min-w-0 p-4">{children}</div>
    </section>
  );
}
