import type { ReactNode } from "react";
import { ApiError } from "@/lib/api/errors";

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex items-center gap-2 border border-line bg-surface px-4 py-6 text-sm text-muted"
    >
      <span className="inline-block h-3 w-3 animate-pulse bg-steel" aria-hidden />
      {label}…
    </div>
  );
}

export function ErrorBlock({
  error,
  onRetry,
  children,
}: {
  error: unknown;
  onRetry?: () => void;
  children?: ReactNode;
}) {
  const api = error instanceof ApiError ? error : null;
  const code = api?.code ?? "ERROR";
  const message =
    api?.message ??
    (error instanceof Error ? error.message : "Something went wrong.");

  return (
    <div className="border border-danger border-t-2 bg-surface">
      <header className="flex items-center gap-2 border-b border-line px-4 py-2">
        <span className="hazard-stripe inline-block h-3 w-3" aria-hidden />
        <span className="label !text-danger">{code}</span>
        {api?.status ? (
          <span className="tnum text-2xs text-muted">HTTP {api.status}</span>
        ) : null}
      </header>
      <div className="space-y-3 p-4 text-sm">
        <p className="text-ink">{message}</p>

        {api?.code === "SCHEMA_MISMATCH" && api.issues?.length ? (
          <details className="border border-line bg-panel p-2 text-xs">
            <summary className="cursor-pointer text-muted">
              Contract mismatch — {api.issues.length} field
              {api.issues.length > 1 ? "s" : ""}
            </summary>
            <ul className="mt-2 space-y-1 font-mono">
              {api.issues.slice(0, 8).map((iss, i) => (
                <li key={i}>
                  <span className="text-danger">{iss.path.join(".") || "(root)"}</span>{" "}
                  — {iss.message}
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        {children}

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyBlock({ children }: { children: ReactNode }) {
  return (
    <div className="border border-dashed border-line bg-surface px-4 py-8 text-center text-sm text-muted">
      {children}
    </div>
  );
}
