"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { ReviewQueueRow } from "@/components/review/ReviewQueueRow";
import { getReviewQueue } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { useRole } from "@/lib/api/auth-store";
import { can } from "@/lib/rbac";
import { SITES } from "@/lib/ontology";

type Sort = "oldest" | "newest" | "confidence_asc";

const SORT_LABEL: Record<Sort, string> = {
  oldest: "Oldest first",
  newest: "Newest first",
  confidence_asc: "Lowest confidence first",
};

export default function ReviewQueuePage() {
  const role = useRole();
  const allowed = can(role, "view_review_queue");

  const [site, setSite] = useState("");
  const [sort, setSort] = useState<Sort>("oldest");
  const [cleared, setCleared] = useState<Set<string>>(new Set());

  const { data, error, loading, reload } = useAsync(
    () => getReviewQueue({ site: site || undefined, sort }),
    [site, sort]
  );

  const items = (data?.items ?? []).filter((i) => !cleared.has(i.report_id));

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">HSE Review Queue</h1>
        <p className="text-sm text-muted">
          Low-confidence and needs-more-info reports awaiting a human decision.
          Two independent reviewers must agree on a correction before it feeds
          model retraining.
        </p>
      </div>

      {!allowed ? (
        <Panel title="Not available for this role" tone="caution">
          <p className="text-sm text-muted">
            The review queue is for HSE reviewers and managers. Your role can
            view reports and dashboards but not act on the queue.
          </p>
        </Panel>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="label">Site</span>
              <select
                value={site}
                onChange={(e) => setSite(e.target.value)}
                className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
              >
                <option value="">All sites</option>
                {SITES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="label">Sort</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as Sort)}
                className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
              >
                {(Object.keys(SORT_LABEL) as Sort[]).map((s) => (
                  <option key={s} value={s}>
                    {SORT_LABEL[s]}
                  </option>
                ))}
              </select>
            </label>
            {data && (
              <span className="tnum ml-auto self-center text-xs text-muted">
                {items.length} pending
              </span>
            )}
          </div>

          {loading && <LoadingBlock label="Loading review queue" />}
          {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

          {data && !loading && items.length === 0 && (
            <div className="border border-clear border-t-2 bg-clear/5 p-6 text-center">
              <p className="label !text-clear">Queue clear</p>
              <p className="mt-1 text-sm text-ink">
                {cleared.size > 0
                  ? "Every report you reviewed has been actioned. Nothing else is waiting."
                  : "No reports are waiting for review" +
                    (site ? ` at ${site}` : "") +
                    ". The model is routing confidently."}
              </p>
            </div>
          )}

          {data && !loading && items.length > 0 && (
            <ul className="space-y-2">
              {items.map((item) => (
                <ReviewQueueRow
                  key={item.report_id}
                  item={item}
                  onCleared={(id) =>
                    setCleared((prev) => new Set(prev).add(id))
                  }
                />
              ))}
            </ul>
          )}
        </>
      )}
    </AppShell>
  );
}
