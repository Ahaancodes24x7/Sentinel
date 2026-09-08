"use client";

import { useState } from "react";
import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { Bar } from "@/components/charts/Bar";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { CreateActionPlanForm } from "./CreateActionPlanForm";
import { ImpactTracker } from "./ImpactTracker";
import { getRecommendation } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { USE_MOCKS } from "@/lib/api/client";
import { humanLabel } from "@/lib/ontology";
import type { ActionPlanResponse } from "@/lib/api/schemas";

const CONTROL_ORDER = ["engineering", "administrative", "procedural", "training"];

export function RecommendationDetailView({
  patternId,
  canCreatePlan,
}: {
  patternId: string;
  canCreatePlan: boolean;
}) {
  const { data, error, loading, reload } = useAsync(
    () => getRecommendation(patternId),
    [patternId]
  );
  const [plan, setPlan] = useState<ActionPlanResponse | null>(null);
  const [showForm, setShowForm] = useState(false);

  if (loading) return <LoadingBlock label="Loading recommendation" />;
  if (error) return <ErrorBlock error={error} onRetry={reload} />;
  if (!data) return null;

  const maxBreakdown = Math.max(1, ...Object.values(data.evidence.breakdown));

  return (
    <div className="space-y-4">
      <Panel
        title={data.title}
        aside={<span className="font-mono text-2xs text-muted">{data.pattern_id}</span>}
      >
        {/* Evidence trail */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ["Reports", data.evidence.report_count],
            ["Sites", data.evidence.site_count],
            ["Window", `${data.evidence.window_days}d`],
            ["Members", data.evidence.member_report_ids.length],
          ].map(([l, v]) => (
            <div key={l} className="border border-line bg-panel p-2">
              <p className="label">{l}</p>
              <p className="tnum mt-0.5 text-lg font-bold">{v}</p>
            </div>
          ))}
        </div>

        <div className="mt-4">
          <p className="label mb-1.5">Evidence breakdown</p>
          <ul className="space-y-1.5">
            {Object.entries(data.evidence.breakdown).map(([k, v]) => (
              <li key={k} className="flex items-center gap-3 text-sm">
                <span className="tnum w-8 font-semibold">{v}</span>
                <div className="min-w-0 flex-1">
                  <Bar value={v} max={maxBreakdown} hue="neutral" height={8} label={k} />
                </div>
                <span className="min-w-0 flex-[2] text-xs text-muted">
                  {humanLabel(k)}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-4">
          <p className="label mb-1">Sites</p>
          <div className="flex flex-wrap gap-1">
            {data.evidence.sites.map((s) => (
              <Chip key={s} hue="neutral">
                {s}
              </Chip>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <p className="label mb-1">Member reports</p>
          <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs">
            {data.evidence.member_report_ids.map((id) =>
              id.startsWith("r-") ? (
                <Link
                  key={id}
                  href={`/reports/${encodeURIComponent(id)}`}
                  className="text-focus hover:underline"
                >
                  {id}
                </Link>
              ) : (
                <span key={id} className="text-muted">
                  {id}
                </span>
              )
            )}
          </div>
        </div>
      </Panel>

      <Panel title="Recommended interventions">
        <ol className="divide-y divide-line">
          {[...data.recommended_interventions]
            .sort((a, b) => a.rank - b.rank)
            .map((iv) => (
              <li key={iv.rank} className="flex items-start gap-3 py-2.5">
                <span className="tnum mt-0.5 text-xs text-muted">#{iv.rank}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Chip hue={iv.priority === "HIGH" ? "danger" : "caution"}>
                      {iv.priority}
                    </Chip>
                    <span
                      className="text-2xs uppercase tracking-[0.06em] text-muted"
                      title={`Hierarchy of control: ${
                        CONTROL_ORDER.indexOf(iv.control_level) + 1
                      } of ${CONTROL_ORDER.length}`}
                    >
                      {iv.control_level}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm">{iv.action}</p>
                </div>
              </li>
            ))}
        </ol>

        <div className="mt-3 border-t border-line pt-3">
          <p className="label mb-1">Expected objective</p>
          {/* verbatim API template text — never reworded toward a causal claim */}
          <p className="border-l-2 border-line pl-3 text-sm leading-6 text-ink">
            {data.expected_objective}
          </p>
        </div>
      </Panel>

      {/* Action plan */}
      {plan ? (
        <ImpactTracker actionPlanId={plan.action_plan_id} canManage={canCreatePlan} />
      ) : canCreatePlan ? (
        showForm ? (
          <CreateActionPlanForm
            rec={data}
            onCreated={(r) => {
              setPlan(r);
              setShowForm(false);
            }}
          />
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setShowForm(true)}
              className="bg-steel px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg"
            >
              Create action plan
            </button>
            {USE_MOCKS && data.pattern_id === "c17" && (
              <button
                type="button"
                onClick={() =>
                  setPlan({
                    action_plan_id: "ap_seed01",
                    pattern_id: "c17",
                    status: "in_progress",
                  })
                }
                className="border border-line bg-panel px-3 py-2 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
              >
                View a sample tracked plan
              </button>
            )}
          </div>
        )
      ) : (
        <Panel title="Create action plan" tone="caution">
          <p className="text-sm text-muted">
            Committing to an action plan is an HSE Manager action. Your role can
            review the evidence and interventions but not create the plan.
          </p>
        </Panel>
      )}
    </div>
  );
}
