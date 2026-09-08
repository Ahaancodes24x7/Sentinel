"use client";

import { useId, useState } from "react";
import { LSR_TAGS } from "@/lib/ontology";
import { submitReviewAction } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import type {
  ReviewActionRequest,
  ReviewActionResponse,
} from "@/lib/api/schemas";

type Action = "confirm" | "correct" | "reject";

const ACTIONS: { value: Action; label: string; hint: string }[] = [
  { value: "confirm", label: "Confirm", hint: "The classification is correct as shown." },
  { value: "correct", label: "Correct", hint: "The classification is wrong — record the right label." },
  { value: "reject", label: "Reject", hint: "This report should not be in the queue." },
];

/**
 * Per-report human-in-the-loop action. `correct` conditionally reveals the
 * corrected-label inputs; the corrected SIF-potential answer is required for
 * `correct` (the backend 422s without it).
 */
export function ReviewActionForm({
  reportId,
  currentSif,
  currentLsr,
  onResult,
}: {
  reportId: string;
  currentSif: boolean;
  currentLsr: string;
  onResult: (r: ReviewActionResponse, action: Action) => void;
}) {
  const gid = useId();
  const [action, setAction] = useState<Action | null>(null);
  const [correctedSif, setCorrectedSif] = useState<boolean | null>(null);
  // Starts unset on purpose — pre-filling the model's own tag anchors the
  // reviewer toward re-confirming it. Forces a deliberate choice.
  const [correctedLsr, setCorrectedLsr] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsCorrectedSif = action === "correct" && correctedSif === null;
  const needsCorrectedLsr = action === "correct" && !correctedLsr;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!action) return;
    if (needsCorrectedSif) {
      setError("Select the corrected SIF-potential value before submitting.");
      return;
    }
    if (needsCorrectedLsr) {
      setError(
        "Choose the correct LSR tag — pick the model's tag again if it's right."
      );
      return;
    }
    setSubmitting(true);
    setError(null);

    const body: ReviewActionRequest =
      action === "correct"
        ? {
            action,
            corrected_sif_potential: correctedSif,
            corrected_lsr_tag: correctedLsr || null,
            reviewer_notes: notes.trim() || null,
          }
        : { action, reviewer_notes: notes.trim() || null };

    try {
      const res = await submitReviewAction(reportId, body);
      onResult(res, action);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not record the action. Try again."
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <fieldset>
        <legend className="label mb-1.5">Decision</legend>
        <div className="grid gap-px sm:grid-cols-3">
          {ACTIONS.map((a) => {
            const on = action === a.value;
            return (
              <label
                key={a.value}
                className={`flex cursor-pointer flex-col gap-0.5 border p-2.5 text-sm ${
                  on
                    ? "border-focus bg-panel font-semibold"
                    : "border-line hover:bg-panel"
                }`}
              >
                <span className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`${gid}-action`}
                    value={a.value}
                    checked={on}
                    onChange={() => {
                      setAction(a.value);
                      setError(null);
                    }}
                    className="accent-focus"
                  />
                  {a.label}
                </span>
                <span className="pl-6 text-2xs font-normal text-muted">
                  {a.hint}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {action === "correct" && (
        <div className="space-y-3 border-l-2 border-caution bg-caution/5 p-3">
          <fieldset>
            <legend className="label mb-1">
              Corrected SIF potential <span className="text-danger">*</span>
            </legend>
            <p className="mb-1.5 text-2xs text-muted">
              Model said{" "}
              <span className="font-mono">
                {currentSif ? "SIF-potential" : "not SIF-potential"}
              </span>
              .
            </p>
            <div className="flex gap-4 text-sm">
              {[
                { v: true, l: "SIF-potential" },
                { v: false, l: "Not SIF-potential" },
              ].map((o) => (
                <label key={o.l} className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    name={`${gid}-sif`}
                    checked={correctedSif === o.v}
                    onChange={() => {
                      setCorrectedSif(o.v);
                      setError(null);
                    }}
                    className="accent-focus"
                  />
                  {o.l}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="block">
            <span className="label">
              Corrected LSR tag <span className="text-danger">*</span>
            </span>
            <p className="mb-1.5 text-2xs text-muted">
              Model tagged <span className="font-mono">{currentLsr}</span>.
            </p>
            <select
              value={correctedLsr}
              onChange={(e) => {
                setCorrectedLsr(e.target.value);
                setError(null);
              }}
              className="mt-1 w-full border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
            >
              <option value="" disabled>
                Select correct LSR tag…
              </option>
              {LSR_TAGS.map((t) => (
                <option key={t} value={t}>
                  {t}
                  {t === currentLsr ? "  — model's original, unchanged" : ""}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {action && (
        <label className="block">
          <span className="label">
            Reviewer notes {action === "reject" ? "" : "(optional)"}
          </span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder={
              action === "correct"
                ? "What did the follow-up establish?"
                : action === "reject"
                  ? "Why should this leave the queue?"
                  : "Anything worth recording alongside the confirmation."
            }
            className="mt-1 w-full border border-line bg-surface px-2 py-1.5 font-mono text-xs focus-visible:border-focus"
          />
        </label>
      )}

      {error && (
        <p
          role="alert"
          className="border-l-2 border-danger bg-danger/5 px-3 py-2 text-xs text-danger"
        >
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!action || submitting}
        className="bg-steel px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg disabled:opacity-50"
      >
        {submitting ? "Recording…" : "Record decision"}
      </button>
    </form>
  );
}
