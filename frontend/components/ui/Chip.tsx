import type { ReactNode } from "react";
import { HUE_VAR, type StatusHue } from "@/lib/ontology";

/** A stamped tag — square, bordered, uppercase. LOTO-tag vernacular. */
export function Chip({
  children,
  hue = "neutral",
  solid = false,
  className = "",
}: {
  children: ReactNode;
  hue?: StatusHue;
  solid?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 border px-2 py-[3px] text-2xs font-semibold uppercase tracking-[0.06em] ${className}`}
      style={
        solid
          ? { background: HUE_VAR[hue], color: "#fff", borderColor: HUE_VAR[hue] }
          : { color: HUE_VAR[hue], borderColor: HUE_VAR[hue] }
      }
    >
      {children}
    </span>
  );
}
