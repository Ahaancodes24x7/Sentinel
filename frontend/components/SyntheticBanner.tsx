/**
 * Persistent banner distinguishing synthetic demo data from real data.
 * Non-negotiable guardrail (backend spec §3.4 / frontend rule 3): any screen
 * showing report data must carry this — it is not a footnote.
 */
export function SyntheticBanner({
  source,
}: {
  source: "synthetic" | "real" | "mixed" | null;
}) {
  if (source === "real" || source == null) return null;

  const text =
    source === "mixed"
      ? "This view mixes synthetic demo data with real reports. Synthetic rows are tagged individually."
      : "Synthetic data — demo dataset. These reports are generated, not real site incidents.";

  return (
    <div
      role="status"
      className="flex items-center gap-2 border-y-2 border-caution bg-caution/10 px-4 py-1.5 text-xs font-semibold text-ink"
    >
      <span className="hazard-stripe inline-block h-3 w-3 shrink-0" aria-hidden />
      <span className="uppercase tracking-[0.06em] text-caution">
        {source === "mixed" ? "Mixed data" : "Synthetic data"}
      </span>
      <span className="font-normal text-muted">{text}</span>
    </div>
  );
}
