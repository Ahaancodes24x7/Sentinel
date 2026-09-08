"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { SummaryHeader } from "@/components/action/SummaryHeader";
import { RecommendationDetailView } from "@/components/action/RecommendationDetailView";
import { listRecommendations } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { useRole } from "@/lib/api/auth-store";
import { can } from "@/lib/rbac";

export default function ActionCenterPage() {
  const role = useRole();
  const canCreatePlan = can(role, "create_action_plan");
  const { data, error, loading, reload } = useAsync(
    () => listRecommendations(),
    []
  );
  const [selected, setSelected] = useState<string | null>(null);

  const recs = data?.recommendations ?? [];
  const active = selected ?? recs[0]?.pattern_id ?? null;

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">SIF Action Center</h1>
        <p className="text-sm text-muted">
          High-priority precursor patterns, their evidence trail, and the
          interventions recommended against them.
        </p>
      </div>

      <div className="mb-5">
        <SummaryHeader />
      </div>

      {loading && <LoadingBlock label="Loading recommendations" />}
      {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

      {data && !loading && recs.length === 0 && (
        <div className="border border-clear border-t-2 bg-clear/5 p-6 text-center">
          <p className="label !text-clear">No high-priority patterns</p>
          <p className="mt-1 text-sm text-ink">
            No precursor pattern currently meets the threshold for a
            recommended intervention.
          </p>
        </div>
      )}

      {data && !loading && recs.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <Panel title={`Patterns (${recs.length})`}>
            <ul className="divide-y divide-line">
              {recs.map((r) => {
                const on = r.pattern_id === active;
                return (
                  <li key={r.pattern_id}>
                    <button
                      type="button"
                      onClick={() => setSelected(r.pattern_id)}
                      aria-current={on ? "true" : undefined}
                      className={`w-full py-2.5 text-left ${
                        on ? "bg-panel" : "hover:bg-panel"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Chip
                          hue={r.priority === "HIGH" ? "danger" : "caution"}
                        >
                          {r.priority}
                        </Chip>
                        <span className="text-sm font-semibold">{r.title}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted">
                        {r.primary_barrier_failure} ·{" "}
                        {r.evidence_summary.report_count} reports ·{" "}
                        {r.evidence_summary.site_count} sites
                      </p>
                      <p className="tnum mt-0.5 text-2xs text-muted">
                        trend {r.evidence_summary.trend_pct > 0 ? "+" : ""}
                        {r.evidence_summary.trend_pct}% over{" "}
                        {r.evidence_summary.window_days}d
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          </Panel>

          <div>
            {active && (
              <RecommendationDetailView
                key={active}
                patternId={active}
                canCreatePlan={canCreatePlan}
              />
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
