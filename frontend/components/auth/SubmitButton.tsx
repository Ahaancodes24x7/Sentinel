import type { ButtonHTMLAttributes, ReactNode } from "react";

/** Full-width steel submit button with a busy state. */
export function SubmitButton({
  busy = false,
  busyLabel = "Working…",
  children,
  ...rest
}: {
  busy?: boolean;
  busyLabel?: string;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...rest}
      disabled={busy || rest.disabled}
      aria-busy={busy || undefined}
      className="w-full bg-steel px-4 py-2.5 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg disabled:opacity-60"
    >
      {busy ? busyLabel : children}
    </button>
  );
}
