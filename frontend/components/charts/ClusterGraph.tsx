"use client";

import { useMemo } from "react";
import { PATTERN_TYPE_META, HUE_VAR } from "@/lib/ontology";
import { useMounted } from "@/lib/use-mounted";
import type { ClusterItem, ClusterEdge } from "@/lib/api/schemas";

const W = 820;
const H = 600;
const CX = W / 2;
const CY = H / 2;

interface Node {
  id: string;
  x: number;
  y: number;
  clusterId: string;
}

/**
 * Hand-rolled node-link graph (SVG). Deterministic radial layout — no physics
 * sim — so positions are stable across renders and legible on a projector.
 *
 * Two entity types, matching the real API response:
 *  - cluster nodes (large, sized by member_count, coloured by pattern_type)
 *  - member-report nodes (small), laid out in a ring around their cluster.
 * `edges` connect member-report ids, drawn with opacity ∝ similarity.
 */
export function ClusterGraph({
  clusters,
  edges,
  selectedId,
  onSelect,
}: {
  clusters: ClusterItem[];
  edges: ClusterEdge[];
  selectedId: string | null;
  onSelect: (clusterId: string) => void;
}) {
  const mounted = useMounted();

  const { clusterNodes, memberNodes, memberIndex } = useMemo(() => {
    const n = Math.max(1, clusters.length);
    const ringR = n === 1 ? 0 : 210;
    const cNodes = clusters.map((c, i) => {
      const a = (2 * Math.PI * i) / n - Math.PI / 2;
      return {
        cluster: c,
        x: CX + ringR * Math.cos(a),
        y: CY + ringR * Math.sin(a),
        r: Math.min(46, 16 + Math.sqrt(c.member_count) * 4),
      };
    });

    const mNodes: Node[] = [];
    const idx = new Map<string, Node>();
    cNodes.forEach(({ cluster, x, y, r }) => {
      const m = Math.max(1, cluster.member_report_ids.length);
      const memR = r + 34;
      cluster.member_report_ids.forEach((mid, j) => {
        const a = (2 * Math.PI * j) / m - Math.PI / 2;
        const node = {
          id: mid,
          x: x + memR * Math.cos(a),
          y: y + memR * Math.sin(a),
          clusterId: cluster.cluster_id,
        };
        mNodes.push(node);
        idx.set(mid, node);
      });
    });

    return { clusterNodes: cNodes, memberNodes: mNodes, memberIndex: idx };
  }, [clusters]);

  const clusterCenter = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    clusterNodes.forEach((c) => map.set(c.cluster.cluster_id, { x: c.x, y: c.y }));
    return map;
  }, [clusterNodes]);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full min-w-[640px]"
        role="group"
        aria-label="Precursor cluster graph"
        style={{
          opacity: mounted ? 1 : 0,
          transition: "opacity 400ms ease",
        }}
      >
        {/* member-to-member similarity edges */}
        {edges.map((e, i) => {
          const a = memberIndex.get(e.source);
          const b = memberIndex.get(e.target);
          if (!a || !b) return null;
          const op = Math.max(0.12, Math.min(0.85, (e.similarity - 0.6) * 2));
          return (
            <line
              key={`e${i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="var(--ink)"
              strokeOpacity={op}
              strokeWidth={1}
            />
          );
        })}

        {/* member -> cluster spokes */}
        {memberNodes.map((m, i) => {
          const c = clusterCenter.get(m.clusterId);
          if (!c) return null;
          const dim = selectedId && selectedId !== m.clusterId;
          return (
            <line
              key={`s${i}`}
              x1={m.x}
              y1={m.y}
              x2={c.x}
              y2={c.y}
              stroke="var(--line)"
              strokeOpacity={dim ? 0.25 : 0.7}
              strokeWidth={1}
            />
          );
        })}

        {/* member nodes */}
        {memberNodes.map((m, i) => {
          const dim = selectedId && selectedId !== m.clusterId;
          return (
            <circle
              key={`m${i}`}
              cx={m.x}
              cy={m.y}
              r={4}
              fill="var(--surface)"
              stroke="var(--muted)"
              strokeWidth={1}
              opacity={dim ? 0.3 : 1}
            >
              <title>{m.id}</title>
            </circle>
          );
        })}

        {/* cluster nodes */}
        {clusterNodes.map(({ cluster, x, y, r }) => {
          const meta = PATTERN_TYPE_META[cluster.pattern_type];
          const hue = HUE_VAR[meta?.hue ?? "neutral"];
          const selected = selectedId === cluster.cluster_id;
          const dim = selectedId && !selected;
          return (
            <g
              key={cluster.cluster_id}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={`Cluster ${cluster.cluster_id}: ${cluster.pattern_summary}, ${cluster.member_count} reports, pattern ${meta?.label}`}
              onClick={() => onSelect(cluster.cluster_id)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") {
                  ev.preventDefault();
                  onSelect(cluster.cluster_id);
                }
              }}
              className="cursor-pointer outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
              opacity={dim ? 0.45 : 1}
            >
              <circle
                cx={x}
                cy={y}
                r={r}
                fill={hue}
                fillOpacity={selected ? 0.32 : 0.16}
                stroke={hue}
                strokeWidth={selected ? 3 : 2}
                strokeDasharray={
                  cluster.pattern_type === "emerging" ? "4 3" : undefined
                }
              />
              <text
                x={x}
                y={y - 2}
                textAnchor="middle"
                className="fill-ink font-mono"
                style={{ fontSize: 12, fontWeight: 600 }}
              >
                {cluster.cluster_id}
              </text>
              <text
                x={x}
                y={y + 12}
                textAnchor="middle"
                className="fill-muted"
                style={{ fontSize: 10 }}
              >
                {cluster.member_count}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function PatternTypeLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5">
      {(
        ["sporadic_high_severity", "emerging", "established"] as const
      ).map((k) => {
        const meta = PATTERN_TYPE_META[k];
        return (
          <li key={k} className="flex items-center gap-1.5 text-2xs uppercase tracking-[0.06em] text-muted">
            <span
              className="inline-block h-3 w-3 border-2"
              style={{
                borderColor: HUE_VAR[meta.hue],
                background: `${HUE_VAR[meta.hue]}29`,
                borderStyle: k === "emerging" ? "dashed" : "solid",
              }}
            />
            {meta.label}
          </li>
        );
      })}
    </ul>
  );
}
