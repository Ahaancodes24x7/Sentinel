"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { SpanText, SpanLegend } from "@/components/report/SpanText";
import { ClassificationPanel } from "@/components/report/ClassificationPanel";
import { FieldConfidence } from "@/components/report/FieldConfidence";
import { getReport } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import { useAsync } from "@/lib/use-async";
import { normalizeFields } from "@/lib/report-fields";

export default function ReportDetailPage({
  params,
}: {
  params: { reportId: string };
}) {
  const id = decodeURIComponent(params.reportId);
  const { data, error, loading, reload } = useAsync(() => getReport(id), [id]);
  const [activeField, setActiveField] = useState<string | null>(null);

  const normalized = useMemo(
    () =>
      data ? normalizeFields(data.extracted_fields, data.report_text) : null,
    [data]
  );

  return (
    <AppShell
      banner={
        <SyntheticBanner source={data ? data.source : "synthetic"} />
      }
    >
      <nav className="mb-3 text-xs text-muted">
        <Link href="/reports" className="text-focus hover:underline">
          Reports
        </Link>{" "}
        / <span className="font-mono">{id}</span>
      </nav>

      {loading && <LoadingBlock label="Loading report" />}

      {!!error && !loading && (
        <ReportError error={error} reportId={id} onRetry={reload} />
      )}

      {data && normalized && !loading && (
        <div className="space-y-4">
          {/* Header strip */}
          <Panel
            title={`Report ${data.report_id}`}
            aside={
              <Chip hue={data.source === "synthetic" ? "caution" : "clear"}>
                {data.source}
              </Chip>
            }
          >
            <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <div>
                <dt className="label">Site</dt>
                <dd className="font-semibold">{data.site}</dd>
              </div>
              <div>
                <dt className="label">Timestamp</dt>
                <dd className="tnum font-mono text-xs">
                  {new Date(data.timestamp).toISOString().replace(".000", "")}
                </dd>
              </div>
              <div>
                <dt className="label">Model version</dt>
                <dd className="font-mono text-xs">
                  {data.classification.model_version}
                </dd>
              </div>
            </dl>
          </Panel>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            {/* Left: original report with span highlights */}
            <div className="space-y-4">
              <Panel
                title="Original report"
                aside={
                  <span className="text-2xs text-muted">
                    {data.report_text.length} chars · spans are exact offsets
                  </span>
                }
              >
                {normalized.hazardIssue && (
                  <p className="mb-3 border-l-2 border-caution bg-caution/5 px-3 py-2 text-xs text-ink">
                    <span className="label !text-caution">
                      Hazard highlight unavailable
                    </span>
                    <br />
                    {normalized.hazardIssue}
                  </p>
                )}
                <SpanText
                  text={data.report_text}
                  spans={normalized.spans}
                  activeField={activeField}
                />
                <div className="mt-4 border-t border-line pt-3">
                  <p className="label mb-1.5">Highlighted fields</p>
                  <SpanLegend
                    fields={normalized.spans.map((s) => s.field)}
                    activeField={activeField}
                    onHover={setActiveField}
                  />
                </div>
              </Panel>
            </div>

            {/* Right: classification + per-field confidence */}
            <div className="space-y-4">
              <ClassificationPanel
                classification={data.classification}
                reviewStatus={data.review_status}
              />
              <FieldConfidence
                rows={normalized.rows}
                activeField={activeField}
                onActivate={setActiveField}
              />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function ReportError({
  error,
  reportId,
  onRetry,
}: {
  error: unknown;
  reportId: string;
  onRetry: () => void;
}) {
  const api = error instanceof ApiError ? error : null;

  if (api?.status === 404) {
    return (
      <ErrorBlock error={error} onRetry={onRetry}>
        <p className="text-xs text-muted">
          No report with id <span className="font-mono">{reportId}</span>. It may
          not have been ingested yet.
        </p>
        <Link
          href="/reports"
          className="inline-block border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
        >
          Back to reports
        </Link>
      </ErrorBlock>
    );
  }

  if (api?.isKnownHazardBug || api?.status === 500) {
    return (
      <ErrorBlock error={error} onRetry={onRetry}>
        <p className="text-xs text-muted">
          This is the known backend integration bug: when a report has hazard
          evidence, <span className="font-mono">GET /reports/{"{id}"}</span>{" "}
          fails because the pipeline&apos;s hazard field shape (
          <span className="font-mono">{"{best_category, matches}"}</span>) does
          not match the endpoint&apos;s{" "}
          <span className="font-mono">{"{text, span, confidence}"}</span> schema.
          The report exists — the detail response just can&apos;t be assembled
          until that&apos;s fixed backend-side.
        </p>
      </ErrorBlock>
    );
  }

  return <ErrorBlock error={error} onRetry={onRetry} />;
}
