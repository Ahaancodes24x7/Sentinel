"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import {
  ClusterGraph,
  PatternTypeLegend,
} from "@/components/charts/ClusterGraph";
import { getClusters } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { PATTERN_TYPE_META, SITES } from "@/lib/ontology";

export default function ClustersPage() {
  const [site, setSite] = useState("");
  const [minSize, setMinSize] = useState(3);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, error, loading, reload } = useAsync(
    () => getClusters({ site: site || undefined, min_cluster_size: minSize }),
    [site, minSize]
  );

  const selected =
    data?.clusters.find((c) => c.cluster_id === selectedId) ?? null;

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Precursor Clusters</h1>
        <p className="text-sm text-muted">
          Groups of near-misses sharing an activity / energy / barrier pattern.
          Node size is the number of member reports; colour is the pattern type.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="label">Site</span>
          <select
            value={site}
            onChange={(e) => {
              setSite(e.target.value);
              setSelectedId(null);
            }}
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
          <span className="label">Min cluster size</span>
          <select
            value={minSize}
            onChange={(e) => setMinSize(Number(e.target.value))}
            className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
          >
            {[1, 2, 3, 5, 8].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <LoadingBlock label="Loading clusters" />}
      {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

      {data && !loading && data.clusters.length === 0 && (
        <div className="border border-clear border-t-2 bg-clear/5 p-6 text-center">
          <p className="label !text-clear">No recurring clusters</p>
          <p className="mt-1 text-sm text-ink">
            No pattern reached {minSize} member reports
            {site ? ` at ${site}` : ""} in this window — near-misses aren&apos;t
            concentrating into a repeat pattern.
          </p>
        </div>
      )}

      {data && !loading && data.clusters.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <Panel
            title={`${data.clusters.length} clusters · ${data.edges.length} links`}
            aside={<PatternTypeLegend />}
          >
            <ClusterGraph
              clusters={data.clusters}
              edges={data.edges}
              selectedId={selectedId}
              onSelect={(id) =>
                setSelectedId((cur) => (cur === id ? null : id))
              }
            />
            <p className="mt-2 text-2xs text-muted">
              Select a cluster node (click, or Tab + Enter) to see its evidence.
            </p>
          </Panel>

          <div className="space-y-4">
            {selected ? (
              <Panel
                title={`Cluster ${selected.cluster_id}`}
                tone={PATTERN_TYPE_META[selected.pattern_type]?.hue === "danger" ? "danger" : "default"}
                aside={
                  <Chip
                    hue={PATTERN_TYPE_META[selected.pattern_type]?.hue ?? "neutral"}
                  >
                    {PATTERN_TYPE_META[selected.pattern_type]?.label ??
                      selected.pattern_type}
                  </Chip>
                }
              >
                <dl className="space-y-3 text-sm">
                  <div>
                    <dt className="label">Pattern</dt>
                    <dd className="mt-0.5 font-mono text-xs leading-5">
                      {selected.pattern_summary}
                    </dd>
                  </div>
                  <div>
                    <dt className="label">Primary LSR</dt>
                    <dd className="mt-1">
                      <Chip hue="neutral">{selected.primary_lsr}</Chip>
                    </dd>
                  </div>
                  <div>
                    <dt className="label">Sites ({selected.sites.length})</dt>
                    <dd className="mt-1 flex flex-wrap gap-1">
                      {selected.sites.map((s) => (
                        <Chip key={s} hue="neutral">
                          {s}
                        </Chip>
                      ))}
                    </dd>
                  </div>
                  <div>
                    <dt className="label">
                      Member reports ({selected.member_count})
                    </dt>
                    <dd className="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs">
                      {selected.member_report_ids.map((id) =>
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
                    </dd>
                    <p className="mt-1 text-2xs text-muted">
                      Grey ids are demo members without a standalone report
                      fixture.
                    </p>
                  </div>
                </dl>
              </Panel>
            ) : (
              <Panel title="Cluster detail">
                <p className="text-sm text-muted">
                  No cluster selected. Pick a node in the graph to see its
                  pattern summary, affected sites, and member reports.
                </p>
              </Panel>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
