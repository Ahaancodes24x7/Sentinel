"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { Toggle } from "@/components/ui/Toggle";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { TrendChart } from "@/components/charts/TrendChart";
import { getTrends } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { SITES, LSR_TAGS } from "@/lib/ontology";

type Granularity = "weekly" | "monthly";

export default function TrendsPage() {
  const [site, setSite] = useState("");
  const [lsr, setLsr] = useState("");
  const [granularity, setGranularity] = useState<Granularity>("weekly");

  const { data, error, loading, reload } = useAsync(
    () =>
      getTrends({
        site: site || undefined,
        lsr_tag: lsr || undefined,
        granularity,
      }),
    [site, lsr, granularity]
  );

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Precursor Trend &amp; Early Warning</h1>
        <p className="text-sm text-muted">
          Reported precursor count per {granularity} period. Alert markers are
          raised by the backend&apos;s change-detection method — their wording is
          shown exactly as returned.
        </p>
      </div>

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
          <span className="label">LSR tag</span>
          <select
            value={lsr}
            onChange={(e) => setLsr(e.target.value)}
            className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
          >
            <option value="">All LSR tags</option>
            {LSR_TAGS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <Toggle
          label="Granularity"
          name="granularity"
          value={granularity}
          onChange={setGranularity}
          options={[
            { value: "weekly", label: "Weekly" },
            { value: "monthly", label: "Monthly" },
          ]}
        />
      </div>

      {loading && <LoadingBlock label="Loading trend series" />}
      {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

      {data && !loading && data.series.length === 0 && (
        <div className="border border-line border-t-2 bg-surface p-6 text-center">
          <p className="label">No reports in range</p>
          <p className="mt-1 text-sm text-muted">
            Nothing was filed for this filter combination.
          </p>
        </div>
      )}

      {data && !loading && data.series.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <Panel title="Precursor count by period">
            <TrendChart
              series={data.series}
              alerts={data.alerts}
              granularity={granularity}
            />
          </Panel>

          <div className="space-y-4">
            <Panel
              title={`Early-warning alerts (${data.alerts.length})`}
              tone={data.alerts.length ? "caution" : "clear"}
            >
              {data.alerts.length === 0 ? (
                <p className="text-sm text-clear">
                  No alerts in this window — the reported precursor rate is
                  within the expected range.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.alerts.map((a) => (
                    <li
                      key={a.period}
                      className="border-l-2 border-caution bg-caution/5 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="tnum font-mono text-xs text-ink">
                          {a.period}
                        </span>
                        <span className="border border-caution px-1.5 py-[1px] text-2xs uppercase tracking-[0.06em] text-caution">
                          {a.method}
                        </span>
                      </div>
                      {/* verbatim API copy — never reworded */}
                      <p className="mt-1 text-sm leading-5 text-ink">
                        {a.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </div>
      )}
    </AppShell>
  );
}
