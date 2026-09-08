/**
 * Static label + semantic-color maps for the SIF ontology.
 * Mirrors aiml/configs/ontology.yaml and backend/schemas.py enums.
 * The backend also exposes GET /ontology, but these values are stable enough
 * to keep locally so the UI renders correct colors before that call returns.
 */

export type StatusHue = "danger" | "caution" | "clear" | "neutral";

export const SITES = [
  "Rig 4",
  "Rig 7",
  "Plant C",
  "Well Site B",
  "Field Station 2",
  "Terminal A",
] as const;

export const ACTIVITIES = [
  "maintenance on process equipment",
  "hot work / welding near process line",
  "lifting operation with mobile crane",
  "confined space entry for tank cleaning",
  "vehicle movement within plant premises",
  "excavation near buried utility line",
  "electrical panel work",
  "scaffolding erection at height",
  "pipeline pigging operation",
  "routine equipment inspection",
] as const;

export const LSR_TAGS = [
  "Energy Isolation",
  "Hot Work",
  "Safe Mechanical Lifting",
  "Line of Fire",
  "Confined Space",
  "Driving",
  "Working at Height",
  "Work Authorisation",
] as const;

export const BUCKETS = [
  "HIGH_CONF_SIF",
  "LOW_CONF_REVIEW",
  "HIGH_CONF_NON_SIF",
  "NEEDS_MORE_INFO",
] as const;

export type Bucket = (typeof BUCKETS)[number];

export const BUCKET_META: Record<
  Bucket,
  { label: string; hue: StatusHue; blurb: string }
> = {
  HIGH_CONF_SIF: {
    label: "High-confidence SIF potential",
    hue: "danger",
    blurb: "Model is confident this near-miss carried serious-injury potential.",
  },
  LOW_CONF_REVIEW: {
    label: "Low confidence — needs review",
    hue: "caution",
    blurb: "Routed to the HSE review queue for a human decision.",
  },
  HIGH_CONF_NON_SIF: {
    label: "High-confidence non-SIF",
    hue: "clear",
    blurb: "Model is confident this near-miss did not carry SIF potential.",
  },
  NEEDS_MORE_INFO: {
    label: "Needs more information",
    hue: "caution",
    blurb: "The report lacks detail needed to classify. Routed for follow-up.",
  },
};

export const BARRIER_STATUS_META: Record<
  string,
  { label: string; hue: StatusHue }
> = {
  confirmed_present: { label: "Confirmed present", hue: "clear" },
  uncertain: { label: "Uncertain", hue: "caution" },
  absent_not_mentioned: { label: "Absent / not mentioned", hue: "danger" },
};

export const EXPOSURE_META: Record<string, { label: string; hue: StatusHue }> = {
  direct_proximity: { label: "Direct proximity", hue: "danger" },
  indirect_proximity: { label: "Indirect proximity", hue: "caution" },
  no_exposure: { label: "No exposure", hue: "clear" },
};

export const PATTERN_TYPE_META: Record<
  string,
  { label: string; hue: StatusHue }
> = {
  established: { label: "Established", hue: "neutral" },
  emerging: { label: "Emerging", hue: "caution" },
  sporadic_high_severity: { label: "Sporadic — high severity", hue: "danger" },
};

/** Per-field highlight hue for the Report Detail span renderer. */
export const FIELD_META: Record<
  string,
  { label: string; color: string }
> = {
  activity: { label: "Activity", color: "#3a4750" },
  hazard: { label: "Hazard", color: "#b3261e" },
  energy_type: { label: "Energy type", color: "#7a3ca8" },
  exposure: { label: "Exposure", color: "#c77700" },
  barrier: { label: "Barrier", color: "#1d6fb8" },
  barrier_status: { label: "Barrier status", color: "#1d6fb8" },
  location: { label: "Location", color: "#2e6b3e" },
};

export const HUE_VAR: Record<StatusHue, string> = {
  danger: "var(--danger)",
  caution: "var(--caution)",
  clear: "var(--clear)",
  neutral: "var(--neutral)",
};

export function humanLabel(raw: string | null | undefined): string {
  if (!raw) return "—";
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function confidenceBand(c: number): { label: string; hue: StatusHue } {
  if (c >= 0.85) return { label: "High", hue: "clear" };
  if (c >= 0.7) return { label: "Moderate", hue: "caution" };
  return { label: "Low", hue: "danger" };
}

/**
 * Trend direction → semantic hue. A rising precursor rate is bad news: large
 * increases read as danger, smaller ones as caution. Falling reads as clear,
 * flat as neutral.
 */
export function trendHue(direction: string, pct: number): StatusHue {
  if (direction === "up") return Math.abs(pct) >= 25 ? "danger" : "caution";
  if (direction === "down") return "clear";
  return "neutral";
}

export function trendGlyph(direction: string): string {
  if (direction === "up") return "▲";
  if (direction === "down") return "▼";
  return "▬";
}
