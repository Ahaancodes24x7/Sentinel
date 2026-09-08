import type {
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";

const box =
  "mt-1 w-full border bg-surface px-3 py-2 text-sm outline-none focus-visible:border-focus";

function Foot({
  error,
  hint,
}: {
  error?: string | null;
  hint?: ReactNode;
}) {
  if (error) return <span className="mt-1 block text-2xs text-danger">{error}</span>;
  if (hint) return <span className="mt-1 block text-2xs text-muted">{hint}</span>;
  return null;
}

/** Labelled text input with an inline error / hint slot. */
export function AuthField({
  label,
  hint,
  error,
  ...input
}: {
  label: string;
  hint?: ReactNode;
  error?: string | null;
} & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <input
        {...input}
        aria-invalid={error ? true : undefined}
        className={`${box} font-mono ${error ? "border-danger" : "border-line"}`}
      />
      <Foot error={error} hint={hint} />
    </label>
  );
}

/** Labelled multi-line input, same treatment as {@link AuthField}. */
export function AuthTextArea({
  label,
  hint,
  error,
  ...area
}: {
  label: string;
  hint?: ReactNode;
  error?: string | null;
} & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <textarea
        {...area}
        aria-invalid={error ? true : undefined}
        className={`${box} resize-y ${error ? "border-danger" : "border-line"}`}
      />
      <Foot error={error} hint={hint} />
    </label>
  );
}
