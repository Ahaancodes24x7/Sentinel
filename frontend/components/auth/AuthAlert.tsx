import type { ReactNode } from "react";

/**
 * Inline status strip for auth forms — a left rule in the semantic colour,
 * matching the console's error/notice vernacular.
 */
export function AuthAlert({
  tone = "danger",
  title,
  children,
}: {
  tone?: "danger" | "clear";
  title?: string;
  children: ReactNode;
}) {
  const rule = tone === "clear" ? "border-clear" : "border-danger";
  const heading = tone === "clear" ? "!text-clear" : "!text-danger";

  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={`border-l-2 ${rule} bg-surface px-3 py-2`}
    >
      {title ? <p className={`label ${heading}`}>{title}</p> : null}
      <p className="mt-0.5 text-xs text-ink">{children}</p>
    </div>
  );
}
