import { HUE_VAR, type StatusHue } from "@/lib/ontology";

/**
 * Segmented readout meter (10 cells) — a control-room gauge, not a smooth
 * progress bar. Used for per-field extraction confidence.
 */
export function Meter({
  value,
  hue = "neutral",
  cells = 10,
  label,
}: {
  value: number; // 0..1
  hue?: StatusHue;
  cells?: number;
  label?: string;
}) {
  const filled = Math.round(Math.min(1, Math.max(0, value)) * cells);
  return (
    <div
      className="flex items-center gap-[3px]"
      role="meter"
      aria-valuenow={Math.round(value * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? "confidence"}
    >
      {Array.from({ length: cells }).map((_, i) => (
        <span
          key={i}
          className="h-3 w-2 border border-line"
          style={{
            background: i < filled ? HUE_VAR[hue] : "transparent",
          }}
        />
      ))}
    </div>
  );
}
