"use client";

import { useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { createActionPlan } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import { SITES } from "@/lib/ontology";
import type {
  RecommendationDetail,
  ActionPlanResponse,
} from "@/lib/api/schemas";

/**
 * "Create Action Plan" — hse_manager only (caller gates on rbac before
 * rendering). Selects intervention ranks + target sites + a planned start date.
 */
export function CreateActionPlanForm({
  rec,
  onCreated,
}: {
  rec: RecommendationDetail;
  onCreated: (r: ActionPlanResponse) => void;
}) {
  const [ranks, setRanks] = useState<number[]>([]);
  const [sites, setSites] = useState<string[]>(rec.evidence.sites.slice(0, 1));
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function toggle<T>(list: T[], v: T): T[] {
    return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (ranks.length === 0) {
      setErr("Select at least one intervention to commit to.");
      return;
    }
    if (sites.length === 0) {
      setErr("Select at least one target site.");
      return;
    }
    if (!date) {
      setErr("Set a planned start date.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const res = await createActionPlan(rec.pattern_id, {
        selected_intervention_ranks: [...ranks].sort((a, b) => a - b),
        target_sites: sites,
        planned_start_date: date,
      });
      onCreated(res);
    } catch (e2) {
      setErr(
        e2 instanceof ApiError ? e2.message : "Could not create the action plan."
      );
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-4 border border-line border-t-2 border-t-steel bg-surface p-4"
    >
      <p className="label">Create action plan</p>

      <fieldset>
        <legend className="label mb-1.5 !normal-case !tracking-normal !text-ink">
          Interventions to commit to
        </legend>
        <ul className="space-y-1.5">
          {rec.recommended_interventions.map((iv) => (
            <li key={iv.rank}>
              <label className="flex cursor-pointer items-start gap-2 border border-line p-2 text-sm hover:bg-panel has-[:checked]:border-focus has-[:checked]:bg-panel">
                <input
                  type="checkbox"
                  className="mt-0.5 accent-focus"
                  checked={ranks.includes(iv.rank)}
                  onChange={() => setRanks((r) => toggle(r, iv.rank))}
                />
                <span>
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="font-mono text-2xs text-muted">
                      #{iv.rank}
                    </span>
                    <Chip hue={iv.priority === "HIGH" ? "danger" : "caution"}>
                      {iv.priority}
                    </Chip>
                    <span className="text-2xs uppercase tracking-[0.06em] text-muted">
                      {iv.control_level}
                    </span>
                  </span>
                  <span className="mt-0.5 block">{iv.action}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <fieldset>
        <legend className="label mb-1.5 !normal-case !tracking-normal !text-ink">
          Target sites
        </legend>
        <div className="flex flex-wrap gap-1.5">
          {SITES.map((s) => {
            const on = sites.includes(s);
            return (
              <label
                key={s}
                className={`cursor-pointer border px-2 py-1 text-xs ${
                  on
                    ? "border-focus bg-panel font-semibold"
                    : "border-line text-muted hover:bg-panel"
                }`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={on}
                  onChange={() => setSites((l) => toggle(l, s))}
                />
                {s}
                {rec.evidence.sites.includes(s) ? " ●" : ""}
              </label>
            );
          })}
        </div>
        <p className="mt-1 text-2xs text-muted">
          ● marks sites already represented in this pattern&apos;s evidence.
        </p>
      </fieldset>

      <label className="block text-sm">
        <span className="label !normal-case !tracking-normal !text-ink">
          Planned start date
        </span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="mt-1 block border border-line bg-surface px-2 py-1.5 font-mono text-sm focus-visible:border-focus"
        />
      </label>

      {err && (
        <p role="alert" className="border-l-2 border-danger bg-danger/5 px-3 py-2 text-xs text-danger">
          {err}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="bg-steel px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg disabled:opacity-50"
      >
        {busy ? "Creating…" : "Create action plan"}
      </button>
    </form>
  );
}
