"use client";

import { getDashboardSummary } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";

function Stat({
  label,
  value,
  hint,
  hue = "ink",
}: {
  label: string;
  value: string;
  hint?: string;
  hue?: "ink" | "danger" | "caution";
}) {
  const color =
    hue === "danger" ? "text-danger" : hue === "caution" ? "text-caution" : "text-ink";
  return (
    <div className="border border-line bg-surface p-3">
      <p className="label">{label}</p>
      <p className={`tnum mt-1 text-2xl font-bold ${color}`}>{value}</p>
      {hint && <p className="mt-0.5 text-2xs text-muted">{hint}</p>}
    </div>
  );
}

export function SummaryHeader() {
  const { data, error, loading, reload } = useAsync(
    () => getDashboardSummary(),
    []
  );

  if (loading) return <LoadingBlock label="Loading summary" />;
  if (error) return <ErrorBlock error={error} onRetry={reload} />;
  if (!data) return null;

  const ingested = new Date(data.last_ingested_at);
  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <Stat
        label="High-priority patterns"
        value={String(data.high_priority_pattern_count)}
        hint="recommended for action"
        hue={data.high_priority_pattern_count > 0 ? "danger" : "ink"}
      />
      <Stat
        label="Reports pending review"
        value={String(data.reports_pending_review)}
        hint="in the HSE review queue"
        hue={data.reports_pending_review > 0 ? "caution" : "ink"}
      />
      <Stat label="Total reports" value={data.total_reports.toLocaleString()} />
      <Stat
        label="Last ingested"
        value={ingested.toISOString().slice(0, 10)}
        hint={ingested.toISOString().slice(11, 16) + "Z"}
      />
    </div>
  );
}
