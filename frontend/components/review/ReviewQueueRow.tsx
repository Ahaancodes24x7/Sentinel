"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Chip } from "@/components/ui/Chip";
import { Meter } from "@/components/ui/Meter";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { SpanText, SpanLegend } from "@/components/report/SpanText";
import { getReport } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { normalizeFields } from "@/lib/report-fields";
import { BUCKET_META, confidenceBand } from "@/lib/ontology";
import type { ReportListItem, ReviewActionResponse } from "@/lib/api/schemas";
import { ReviewActionForm } from "./ReviewActionForm";
import { ReviewResult } from "./ReviewResult";

// Report age from the API `timestamp` field. The backend has no separate
// queue-entry time and orders the queue by this field, so report age is the
// honest label — not an invented "time in queue".
function reportedAgo(iso: string): string {
  const d = Math.floor((Date.now() - +new Date(iso)) / 86_400_000);
  if (d <= 0) return "reported today";
  if (d === 1) return "reported 1 day ago";
  return `reported ${d} days ago`;
}

export function ReviewQueueRow({
  item,
  onCleared,
}: {
  item: ReportListItem;
  onCleared: (reportId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<ReviewActionResponse | null>(null);
  const [submittedAction, setSubmittedAction] =
    useState<"confirm" | "correct" | "reject" | null>(null);
  const reduce = useReducedMotion();

  // Lazy per-row detail — isolates the known hazard-shape 500 to one row.
  const detail = useAsync(
    () => (open ? getReport(item.report_id) : Promise.resolve(null)),
    [open, item.report_id]
  );

  const normalized = useMemo(
    () =>
      detail.data
        ? normalizeFields(detail.data.extracted_fields, detail.data.report_text)
        : null,
    [detail.data]
  );

  const meta = BUCKET_META[item.bucket];
  const band = detail.data
    ? confidenceBand(detail.data.classification.confidence)
    : null;

  return (
    <li className="border border-line bg-surface">
      {/* Summary row — scannable */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2.5">
        <Link
          href={`/reports/${encodeURIComponent(item.report_id)}`}
          className="font-mono text-sm text-focus underline-offset-2 hover:underline"
        >
          {item.report_id}
        </Link>
        <span className="text-sm font-semibold">{item.site}</span>
        <Chip hue={meta.hue}>{item.bucket}</Chip>
        <span className="text-xs text-muted">{item.lsr_tag}</span>
        <span className="tnum text-2xs text-muted">
          {reportedAgo(item.timestamp)}
        </span>

        {detail.data && band && (
          <span className="ml-auto flex items-center gap-2">
            <span className="label">conf</span>
            <Meter value={detail.data.classification.confidence} hue={band.hue} />
            <span className="tnum text-xs text-muted">
              {detail.data.classification.confidence.toFixed(2)}
            </span>
          </span>
        )}

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className={`${
            detail.data && band ? "" : "ml-auto"
          } border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus`}
        >
          {open ? "Collapse" : "Review"}
        </button>
      </div>

      {/* Compact justification preview once detail is available */}
      {open && detail.data && (
        <p className="border-t border-line px-3 py-2 text-xs leading-5 text-muted">
          <span className="label mr-1.5">Model rationale</span>
          {detail.data.classification.justification}
        </p>
      )}

      {open && (
        <motion.div
          initial={reduce ? false : { height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          transition={{ duration: reduce ? 0 : 0.2, ease: "easeOut" }}
          className="overflow-hidden border-t border-line"
        >
          <div className="space-y-4 p-3">
            {detail.loading && <LoadingBlock label="Loading report detail" />}

            {!!detail.error && !detail.loading && (
              <ErrorBlock error={detail.error} onRetry={detail.reload}>
                <p className="text-xs text-muted">
                  The full report couldn&apos;t be loaded (likely the known
                  hazard-shape 500). You can still record a decision below from
                  the queue-level classification.
                </p>
              </ErrorBlock>
            )}

            {detail.data && normalized && (
              <div className="border border-line bg-panel p-3">
                <p className="label mb-1.5">Original report</p>
                {normalized.hazardIssue && (
                  <p className="mb-2 border-l-2 border-caution bg-caution/5 px-2 py-1 text-2xs text-ink">
                    {normalized.hazardIssue}
                  </p>
                )}
                <SpanText
                  text={detail.data.report_text}
                  spans={normalized.spans}
                />
                <div className="mt-2 border-t border-line pt-2">
                  <SpanLegend fields={normalized.spans.map((s) => s.field)} />
                </div>
              </div>
            )}

            {result ? (
              <ReviewResult
                result={result}
                action={submittedAction}
                onDismiss={() => onCleared(item.report_id)}
              />
            ) : (
              <ReviewActionForm
                reportId={item.report_id}
                currentSif={item.sif_potential}
                currentLsr={item.lsr_tag}
                onResult={(r, action) => {
                  setSubmittedAction(action);
                  setResult(r);
                }}
              />
            )}
          </div>
        </motion.div>
      )}
    </li>
  );
}
