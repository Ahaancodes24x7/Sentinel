import { BUCKET_META, HUE_VAR, type Bucket } from "@/lib/ontology";

/**
 * The classification bucket, rendered as a control-room status block.
 * HIGH_CONF_SIF gets the barrier-tape edge — the one place that motif is
 * spent on this screen.
 */
export function BucketBadge({
  bucket,
  confidence,
}: {
  bucket: Bucket;
  confidence: number;
}) {
  const meta = BUCKET_META[bucket];
  const isSif = bucket === "HIGH_CONF_SIF";

  return (
    <div className="flex">
      {isSif && <div className="hazard-stripe w-2 shrink-0" aria-hidden />}
      <div
        className="flex-1 border p-3"
        style={{ borderColor: HUE_VAR[meta.hue] }}
      >
        <div className="flex items-baseline justify-between gap-3">
          <span
            className="font-mono text-sm font-semibold uppercase tracking-[0.04em]"
            style={{ color: HUE_VAR[meta.hue] }}
          >
            {bucket}
          </span>
          <span className="tnum text-sm text-muted">
            conf {confidence.toFixed(2)}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted">{meta.label}</p>
        <p className="mt-1.5 text-2xs leading-4 text-muted">{meta.blurb}</p>
      </div>
    </div>
  );
}
