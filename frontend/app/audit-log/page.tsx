"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { Panel } from "@/components/ui/Panel";
import { LoadingBlock, ErrorBlock } from "@/components/StateBlock";
import { getAuditLog } from "@/lib/api/endpoints";
import { useAsync } from "@/lib/use-async";
import { useRole } from "@/lib/api/auth-store";
import { can } from "@/lib/rbac";

const ENTITY_TYPES = ["report", "review_action", "action_plan"];

export default function AuditLogPage() {
  const role = useRole();
  const allowed = can(role, "view_audit_log");

  const [entityType, setEntityType] = useState("");
  const [actor, setActor] = useState("");
  const [sortDesc, setSortDesc] = useState(true);

  const { data, error, loading, reload } = useAsync(
    () =>
      getAuditLog({
        entity_type: entityType || undefined,
        actor: actor || undefined,
      }),
    [entityType, actor]
  );

  const actors = useMemo(
    () => Array.from(new Set((data?.items ?? []).map((r) => r.actor))).sort(),
    [data]
  );

  const rows = useMemo(() => {
    const list = [...(data?.items ?? [])];
    list.sort((a, b) =>
      sortDesc
        ? b.timestamp.localeCompare(a.timestamp)
        : a.timestamp.localeCompare(b.timestamp)
    );
    return list;
  }, [data, sortDesc]);

  return (
    <AppShell banner={<SyntheticBanner source="synthetic" />}>
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Audit Log</h1>
        <p className="text-sm text-muted">
          Every ingestion, review action, and action-plan change, with actor and
          timestamp.
        </p>
      </div>

      {!allowed ? (
        <Panel title="Not available for this role" tone="caution">
          <p className="text-sm text-muted">
            The audit log is for auditors and HSE managers. HSE reviewers can act
            on the review queue but cannot read the audit trail.
          </p>
        </Panel>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="label">Entity type</span>
              <select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
              >
                <option value="">All</option>
                {ENTITY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="label">Actor</span>
              <select
                value={actor}
                onChange={(e) => setActor(e.target.value)}
                className="mt-1 block border border-line bg-surface px-2 py-1.5 text-sm focus-visible:border-focus"
              >
                <option value="">All actors</option>
                {actors.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </label>
            {data && (
              <span className="tnum ml-auto self-center text-xs text-muted">
                {rows.length} entries
              </span>
            )}
          </div>

          {loading && <LoadingBlock label="Loading audit log" />}
          {!!error && !loading && <ErrorBlock error={error} onRetry={reload} />}

          {data && !loading && rows.length === 0 && (
            <div className="border border-line border-t-2 bg-surface p-6 text-center text-sm text-muted">
              No audit entries match this filter.
            </div>
          )}

          {data && !loading && rows.length > 0 && (
            <Panel title="Audit trail">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line text-left">
                      <th className="label py-2 pr-3">
                        <button
                          type="button"
                          onClick={() => setSortDesc((v) => !v)}
                          className="uppercase tracking-[0.06em] hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
                        >
                          Timestamp {sortDesc ? "▼" : "▲"}
                        </button>
                      </th>
                      <th className="label py-2 pr-3">Entity type</th>
                      <th className="label py-2 pr-3">Entity ID</th>
                      <th className="label py-2 pr-3">Action</th>
                      <th className="label py-2">Actor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-line last:border-0 hover:bg-panel"
                      >
                        <td className="tnum py-1.5 pr-3 font-mono text-xs">
                          {r.timestamp.replace("T", " ").replace("Z", "")}Z
                        </td>
                        <td className="py-1.5 pr-3 text-xs">{r.entity_type}</td>
                        <td className="py-1.5 pr-3 font-mono text-xs text-muted">
                          {r.entity_id}
                        </td>
                        <td className="py-1.5 pr-3 text-xs font-semibold">
                          {r.action}
                        </td>
                        <td className="py-1.5 font-mono text-xs">{r.actor}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      )}
    </AppShell>
  );
}
