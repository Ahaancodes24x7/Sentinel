"use client";

/**
 * Segmented control — a labelled row of mutually exclusive options rendered
 * as a radiogroup. Keyboard: arrow keys move between options (native radio
 * behaviour), Tab moves in/out.
 */
export function Toggle<T extends string>({
  label,
  value,
  options,
  onChange,
  name,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  name: string;
}) {
  return (
    <div>
      <span className="label mb-1 block">{label}</span>
      <div role="radiogroup" aria-label={label} className="inline-flex border border-line">
        {options.map((o, i) => {
          const on = o.value === value;
          return (
            <label
              key={o.value}
              className={`cursor-pointer px-3 py-1.5 text-sm outline-offset-[-2px] has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus ${
                i > 0 ? "border-l border-line" : ""
              } ${
                on
                  ? "bg-steel font-semibold text-steel-fg"
                  : "bg-surface text-muted hover:bg-panel"
              }`}
            >
              <input
                type="radio"
                name={name}
                value={o.value}
                checked={on}
                onChange={() => onChange(o.value)}
                className="sr-only"
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </div>
  );
}
