"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { Toggle } from "@/components/ui/Toggle";
import { Bar } from "@/components/charts/Bar";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { getRankings } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { trendHue, trendGlyph, humanLabel } from "@/lib/ontology";
import type { MetricWeights, RankingRow } from "@/lib/api/schemas";

type Metric = "simple" | "composite";
type GroupBy = "site" | "activity";
type SortBy = "density" | "count";

export default function RankingsPage() {
  const [metric, setMetric] = useState<Metric>("simple");
  const [groupBy, setGroupBy] = useState<GroupBy>("site");
  const [sortBy, setSortBy] = useState<SortBy>("density");

  const { data, error, loading, reload } = useAsync(
    () => getRankings({ metric, group_by: groupBy }),
    [metric, groupBy]
  );

  const rows: RankingRow[] = [...(data?.rankings ?? [])].sort((a, b) =>
    sortBy === "density"
      ? b.density - a.density
      : b.sif_flagged_count - a.sif_flagged_count
  );
  const maxDensity = Math.max(0.0001, ...rows.map((r) => r.density));
  const anyElevated = rows.some((r) => r.density >= 0.1);

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Site &amp; Activity Rankings</h1>
        <p className="text-sm text-muted">
          SIF-precursor density over the last {data?.window_days ?? 42} days,
          ranked {sortBy === "density" ? "by density" : "by flagged count"}.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <Toggle
          label="Metric"
          name="metric"
          value={metric}
          onChange={setMetric}
          options={[
            { value: "simple", label: "Simple" },
            { value: "composite", label: "Composite" },
          ]}
        />
        <Toggle
          label="Group by"
          name="group_by"
          value={groupBy}
          onChange={setGroupBy}
          options={[
            { value: "site", label: "Site" },
            { value: "activity", label: "Activity" },
          ]}
        />
        <Toggle
          label="Sort"
          name="sort"
          value={sortBy}
          onChange={setSortBy}
          options={[
            { value: "density", label: "Density" },
            { value: "count", label: "Count" },
          ]}
        />
      </div>

      {/* Non-negotiable: composite metric must expose its weights. */}
      {metric === "composite" && (
        <WeightsDisclosure weights={data?.weights} />
      )}

      {loading && <LoadingBlock label="Loading rankings" />}
      {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

      {data && !loading && rows.length === 0 && (
        <div className="border border-clear border-t-2 bg-clear/5 p-6 text-center">
          <p className="label !text-clear">No activity in this window</p>
          <p className="mt-1 text-sm text-ink">
            No reports were filed for any {groupBy} in the last{" "}
            {data.window_days} days.
          </p>
        </div>
      )}

      {data && !loading && rows.length > 0 && (
        <Panel
          title={`${rows.length} ${groupBy === "site" ? "sites" : "activities"}`}
          aside={
            !anyElevated ? (
              <span className="text-2xs text-clear">
                No {groupBy} above 0.10 density — precursor load is spread thin
              </span>
            ) : null
          }
        >
          <ol className="divide-y divide-line">
            {rows.map((r, i) => {
              const hue = trendHue(r.trend_direction, r.trend_pct);
              return (
                <li key={r.group} className="py-3">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="tnum w-6 text-xs text-muted">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="text-sm font-semibold">
                      {groupBy === "activity" ? humanLabel(r.group) : r.group}
                    </span>
                    <Chip hue="neutral" className="ml-1">
                      {r.primary_lsr}
                    </Chip>
                    <span
                      className="tnum ml-auto flex items-center gap-1 text-xs font-semibold"
                      style={{ color: `var(--${hue})` }}
                      title={`Trend ${r.trend_direction} ${r.trend_pct}%`}
                    >
                      {trendGlyph(r.trend_direction)}{" "}
                      {r.trend_pct > 0 ? "+" : ""}
                      {r.trend_pct}%
                    </span>
                  </div>

                  <div className="mt-2 flex items-center gap-3 pl-9">
                    <div className="min-w-0 flex-1">
                      <Bar
                        value={r.density}
                        max={maxDensity}
                        hue={
                          r.density >= 0.15
                            ? "danger"
                            : r.density >= 0.08
                              ? "caution"
                              : "neutral"
                        }
                        label={`${r.group} density ${r.density}`}
                      />
                    </div>
                    <span className="tnum shrink-0 text-xs text-muted">
                      density{" "}
                      <span className="font-semibold text-ink">
                        {r.density.toFixed(3)}
                      </span>
                    </span>
                    <span className="tnum shrink-0 text-xs text-muted">
                      {r.sif_flagged_count}/{r.total_reports} flagged
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
        </Panel>
      )}
    </AppShell>
  );
}

function WeightsDisclosure({
  weights,
}: {
  weights: MetricWeights | null | undefined;
}) {
  const LABELS: Record<string, string> = {
    w1_severity_adjusted_rate: "Severity-adjusted precursor rate",
    w2_recurrence: "Recurrence / repeat-pattern weight",
    w3_severity_weighting: "Severity weighting",
  };
  return (
    <details
      open
      className="mb-4 border border-line border-t-2 border-t-steel bg-surface"
    >
      <summary className="label cursor-pointer px-4 py-2">
        How the composite score is weighted
      </summary>
      <div className="border-t border-line p-4">
        {weights ? (
          <ul className="space-y-2">
            {Object.entries(weights).map(([k, raw]) => {
              const v = Number(raw);
              return (
                <li key={k} className="flex items-center gap-3 text-sm">
                  <span className="tnum w-14 font-semibold">
                    {(v * 100).toFixed(0)}%
                  </span>
                  <div className="min-w-0 flex-1">
                    <Bar value={v} max={1} hue="neutral" height={8} label={k} />
                  </div>
                  <span className="min-w-0 flex-1 text-xs text-muted">
                    {LABELS[k] ?? k}
                  </span>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-xs text-muted">
            Weights not returned by the API for this response.
          </p>
        )}
        <p className="mt-3 text-2xs text-muted">
          Weights are near-equal and tunable. The composite score is a weighted
          combination of these factors — shown here rather than applied silently.
        </p>
      </div>
    </details>
  );
}
