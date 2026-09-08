"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { ImpactChart } from "@/components/charts/ImpactChart";
import { getActionPlanImpact, updateActionPlan } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { ApiError } from "@/lib/api/errors";

/**
 * Before/after outcome tracker for one action plan. Rule: the API `disclaimer`
 * is rendered verbatim, directly adjacent to the chart — never in a tooltip,
 * never reworded. This is the most causally-loaded view in the app.
 */
export function ImpactTracker({
  actionPlanId,
  canManage,
}: {
  actionPlanId: string;
  canManage: boolean;
}) {
  const { data, error, loading, reload } = useAsync(
    () => getActionPlanImpact(actionPlanId),
    [actionPlanId]
  );
  const [marking, setMarking] = useState(false);
  const [markErr, setMarkErr] = useState<string | null>(null);
  const [markedStarted, setMarkedStarted] = useState(false);

  async function markStarted() {
    setMarking(true);
    setMarkErr(null);
    try {
      await updateActionPlan(actionPlanId, {
        actual_start_date: new Date().toISOString().slice(0, 10),
        status: "in_progress",
      });
      setMarkedStarted(true);
      reload();
    } catch (e) {
      setMarkErr(
        e instanceof ApiError ? e.message : "Could not update the plan."
      );
    } finally {
      setMarking(false);
    }
  }

  return (
    <Panel
      title={`Impact tracking · ${actionPlanId}`}
      aside={
        data ? (
          <Chip hue={data.pct_change < 0 ? "clear" : data.pct_change > 0 ? "danger" : "neutral"}>
            {data.pct_change > 0 ? "+" : ""}
            {data.pct_change}% vs baseline
          </Chip>
        ) : null
      }
    >
      {loading && <LoadingBlock label="Loading impact data" />}
      {!!error && !loading && (
        <ErrorBlock error={error} onRetry={reload}>
          <p className="text-xs text-muted">
            Impact data is only available once a plan exists on the backend.
          </p>
        </ErrorBlock>
      )}

      {data && !loading && (
        <div className="space-y-3">
          {data.after_weekly.length === 0 ? (
            <p className="border border-dashed border-line bg-panel px-3 py-4 text-sm text-muted">
              Intervention start date is{" "}
              <span className="font-mono">{data.intervention_start_date}</span>.
              No post-intervention weeks have completed yet — the before/after
              comparison will populate as reports accumulate.
            </p>
          ) : (
            <ImpactChart impact={data} />
          )}

          {/* Non-negotiable: disclaimer verbatim, adjacent to the chart. */}
          <p className="border-l-2 border-neutral bg-panel px-3 py-2 text-xs leading-5 text-ink">
            <span className="label mr-1.5">Note</span>
            {data.disclaimer}
          </p>

          {canManage && (
            <div className="border-t border-line pt-3">
              {markedStarted ? (
                <p className="text-xs text-clear">
                  Plan marked as started — actual start date recorded.
                </p>
              ) : (
                <button
                  type="button"
                  onClick={markStarted}
                  disabled={marking}
                  className="border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus disabled:opacity-50"
                >
                  {marking ? "Updating…" : "Mark plan as actually started"}
                </button>
              )}
              {markErr && (
                <p role="alert" className="mt-1 text-xs text-danger">
                  {markErr}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
