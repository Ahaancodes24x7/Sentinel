import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { BucketBadge } from "./BucketBadge";
import type { Classification } from "@/lib/api/schemas";

/**
 * Renders the model's classification verbatim. `justification` and `lsr_tag`
 * are fixed backend strings — shown as-is, never reworded, never presented as
 * a prediction of an outcome.
 */
export function ClassificationPanel({
  classification,
  reviewStatus,
}: {
  classification: Classification;
  reviewStatus: string;
}) {
  return (
    <Panel
      title="Classification"
      tone={classification.bucket === "HIGH_CONF_SIF" ? "danger" : "default"}
    >
      <BucketBadge
        bucket={classification.bucket}
        confidence={classification.confidence}
      />

      <dl className="mt-4 space-y-4">
        <div>
          <dt className="label">Life-Saving Rule</dt>
          <dd className="mt-1">
            <Chip hue="neutral">{classification.lsr_tag}</Chip>
          </dd>
        </div>

        <div>
          <dt className="label">SIF potential</dt>
          <dd className="mt-1 text-sm">
            {classification.sif_potential ? (
              <span className="font-semibold text-danger">
                Yes — carried serious-injury potential
              </span>
            ) : (
              <span className="font-semibold text-clear">
                No — no serious-injury potential identified
              </span>
            )}
          </dd>
        </div>

        <div>
          <dt className="label">Justification</dt>
          <dd className="mt-1 border-l-2 border-line pl-3 text-sm leading-6 text-ink">
            {classification.justification}
          </dd>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
          <span className="label">Model</span>
          <span className="tnum font-mono text-xs text-muted">
            {classification.model_version}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="label">Review status</span>
          <Chip hue={reviewStatus === "pending" ? "caution" : "clear"}>
            {reviewStatus}
          </Chip>
        </div>
      </dl>
    </Panel>
  );
}
