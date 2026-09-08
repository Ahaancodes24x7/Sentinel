import { Chip } from "@/components/ui/Chip";
import type { ReviewActionResponse } from "@/lib/api/schemas";

/**
 * Post-action state. When two independent reviewers agree on a correction the
 * report is promoted to the training queue — that's how the system improves,
 * so it gets a distinct, explicit confirmation rather than a silent field.
 */
export function ReviewResult({
  result,
  action,
  onDismiss,
}: {
  result: ReviewActionResponse;
  action: "confirm" | "correct" | "reject" | null;
  onDismiss: () => void;
}) {
  if (result.promoted_to_training_queue) {
    return (
      <div className="border border-clear border-t-2 bg-clear/5 p-4">
        <div className="flex items-center gap-2">
          <span
            className="grid h-5 w-5 place-items-center bg-clear text-xs font-bold text-white"
            aria-hidden
          >
            ✓✓
          </span>
          <span className="label !text-clear">Promoted to training queue</span>
        </div>
        <p className="mt-2 text-sm leading-6 text-ink">
          Two independent reviewers have now recorded the same corrected label
          for <span className="font-mono">{result.report_id}</span>. The
          2-reviewer-agreement gate is met — this report joins the training queue
          and will feed the next model retraining cycle.
        </p>
        <p className="mt-1 font-mono text-2xs text-muted">
          action {result.review_action_id} · {result.status}
        </p>
        <button
          type="button"
          onClick={onDismiss}
          className="mt-3 border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
        >
          Clear from queue
        </button>
      </div>
    );
  }

  return (
    <div className="border border-line border-t-2 border-t-clear bg-surface p-4">
      <div className="flex items-center gap-2">
        <Chip hue="clear">recorded</Chip>
        <span className="font-mono text-2xs text-muted">
          {result.review_action_id}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-ink">
        {action === "correct" ? (
          <>
            Correction logged. One reviewer decision so far — a second
            independent reviewer must record the same corrected label before it
            is used for training.
          </>
        ) : action === "reject" ? (
          <>Report rejected from the review queue.</>
        ) : (
          <>Classification confirmed as shown.</>
        )}
      </p>
      <button
        type="button"
        onClick={onDismiss}
        className="mt-3 border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
      >
        Clear from queue
      </button>
    </div>
  );
}
