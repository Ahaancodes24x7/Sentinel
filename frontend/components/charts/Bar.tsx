"use client";

import { HUE_VAR, type StatusHue } from "@/lib/ontology";
import { useMounted } from "@/lib/use-mounted";

/**
 * Hand-rolled horizontal bar (SVG). A control-room readout, not a chart-kit
 * component: square ends, hairline frame, fill in a semantic hue. Draws in
 * from the left on mount (CSS transition; neutralised under reduced-motion).
 */
export function Bar({
  value,
  max,
  hue = "neutral",
  height = 12,
  label,
}: {
  value: number;
  max: number;
  hue?: StatusHue;
  height?: number;
  label?: string;
}) {
  const mounted = useMounted();
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;

  return (
    <svg
      width="100%"
      height={height}
      className="block overflow-visible"
      role="img"
      aria-label={label ?? `${value} of ${max}`}
      preserveAspectRatio="none"
    >
      <rect x={0} y={0} width="100%" height={height} fill="var(--panel)" />
      <rect
        x={0}
        y={0}
        width={`${mounted ? pct : 0}%`}
        height={height}
        fill={HUE_VAR[hue]}
        style={{ transition: "width 500ms ease" }}
      />
      <rect
        x={0.5}
        y={0.5}
        width="99%"
        height={height - 1}
        fill="none"
        stroke="var(--line)"
        strokeWidth={1}
      />
    </svg>
  );
}
