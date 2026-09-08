"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Chip } from "@/components/ui/Chip";
import { LoadingBlock, ErrorBlock, EmptyBlock } from "@/components/StateBlock";
import { listReports, type ReportFilters } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { BUCKET_META, BUCKETS, SITES, LSR_TAGS } from "@/lib/ontology";

const SIF_OPTS = [
  { value: "", label: "Any SIF potential" },
  { value: "true", label: "SIF-potential only" },
  { value: "false", label: "Non-SIF only" },
];

export default function ReportsPage() {
  const [filters, setFilters] = useState<{
    site: string;
    bucket: string;
    lsr_tag: string;
    source: string;
    sif: string;
    date_from: string;
    date_to: string;
  }>({
    site: "",
    bucket: "",
    lsr_tag: "",
    source: "",
    sif: "",
    date_from: "",
    date_to: "",
  });

  const query: ReportFilters = {
    limit: 100,
    site: filters.site || undefined,
    bucket: filters.bucket || undefined,
    lsr_tag: filters.lsr_tag || undefined,
    source: filters.source || undefined,
    sif_potential: filters.sif ? filters.sif === "true" : undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  };

  const { data, error, loading, reload } = useAsync(
    () => listReports(query),
    [JSON.stringify(query)]
  );

  const anyFilter = Object.values(filters).some(Boolean);
  const set = (k: keyof typeof filters, v: string) =>
    setFilters((f) => ({ ...f, [k]: v }));

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Reports</h1>
        <p className="text-sm text-muted">
          Browse all ingested reports. Filter by site, SIF potential, bucket, LSR
          tag, date range, and source.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Select label="Site" value={filters.site} onChange={(v) => set("site", v)}>
          <option value="">All sites</option>
          {SITES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </Select>
        <Select
          label="SIF potential"
          value={filters.sif}
          onChange={(v) => set("sif", v)}
        >
          {SIF_OPTS.map((o) => (
            <option key={o.label} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          label="Bucket"
          value={filters.bucket}
          onChange={(v) => set("bucket", v)}
        >
          <option value="">All buckets</option>
          {BUCKETS.map((b) => (
            <option key={b}>{b}</option>
          ))}
        </Select>
        <Select
          label="LSR tag"
          value={filters.lsr_tag}
          onChange={(v) => set("lsr_tag", v)}
        >
          <option value="">All LSR tags</option>
          {LSR_TAGS.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </Select>
        <Select
          label="Source"
          value={filters.source}
          onChange={(v) => set("source", v)}
        >
          <option value="">Synthetic + real</option>
          <option value="synthetic">Synthetic</option>
          <option value="real">Real</option>
        </Select>
        <label className="text-sm">
          <span className="label">From</span>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => set("date_from", e.target.value)}
            className="mt-1 block border border-line bg-surface px-2 py-1.5 font-mono text-xs focus-visible:border-focus"
          />
        </label>
        <label className="text-sm">
          <span className="label">To</span>
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => set("date_to", e.target.value)}
            className="mt-1 block border border-line bg-surface px-2 py-1.5 font-mono text-xs focus-visible:border-focus"
          />
        </label>
        {anyFilter && (
          <button
            type="button"
            onClick={() =>
              setFilters({
                site: "",
                bucket: "",
                lsr_tag: "",
                source: "",
                sif: "",
                date_from: "",
                date_to: "",
              })
            }
            className="border border-line bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.06em] hover:border-focus"
          >
            Clear filters
          </button>
        )}
      </div>

      {loading && <LoadingBlock label="Loading reports" />}
      {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

      {data && !loading && (
        <Panel
          title={`${data.total} report${data.total === 1 ? "" : "s"}`}
          aside={
            data.total >= 100 ? (
              <span className="text-2xs text-muted">showing first 100</span>
            ) : null
          }
        >
          {data.items.length === 0 ? (
            <EmptyBlock>
              {anyFilter
                ? "No reports match these filters."
                : "No reports have been ingested yet."}
            </EmptyBlock>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line text-left">
                    <th className="label py-2 pr-3">Report</th>
                    <th className="label py-2 pr-3">Site</th>
                    <th className="label py-2 pr-3">Timestamp</th>
                    <th className="label py-2 pr-3">SIF</th>
                    <th className="label py-2 pr-3">Bucket</th>
                    <th className="label py-2">LSR tag</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => {
                    const meta = BUCKET_META[r.bucket];
                    return (
                      <tr
                        key={r.report_id}
                        className="border-b border-line last:border-0 hover:bg-panel"
                      >
                        <td className="py-2 pr-3">
                          <Link
                            href={`/reports/${encodeURIComponent(r.report_id)}`}
                            className="font-mono text-focus underline-offset-2 hover:underline"
                          >
                            {r.report_id}
                          </Link>
                        </td>
                        <td className="py-2 pr-3">{r.site}</td>
                        <td className="tnum py-2 pr-3 font-mono text-xs text-muted">
                          {new Date(r.timestamp)
                            .toISOString()
                            .slice(0, 16)
                            .replace("T", " ")}
                          Z
                        </td>
                        <td className="py-2 pr-3">
                          {r.sif_potential ? (
                            <span className="font-semibold text-danger">yes</span>
                          ) : (
                            <span className="text-muted">no</span>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          <Chip hue={meta.hue}>{r.bucket}</Chip>
                        </td>
                        <td className="py-2 text-xs">{r.lsr_tag}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
    </AppShell>
  );
}

function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="text-sm">
      <span className="label">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
      >
        {children}
      </select>
    </label>
  );
}
