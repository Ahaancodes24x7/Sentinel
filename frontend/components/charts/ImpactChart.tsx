"use client";

import { useId, useMemo } from "react";
import { useMounted } from "@/lib/use-mounted";
import type { ImpactResponse } from "@/lib/api/schemas";

const W = 620;
const H = 260;
const PAD = { top: 16, right: 16, bottom: 40, left: 44 };

/**
 * Before / after precursor-rate chart (SVG). The "before" baseline is a flat
 * reference band; the weekly post-intervention rates are a line. Deliberately
 * plain — the causal-claim discipline lives in the disclaimer rendered next to
 * this chart, not in the visualisation.
 */
export function ImpactChart({ impact }: { impact: ImpactResponse }) {
  const mounted = useMounted();
  const clipId = useId();

  const model = useMemo(() => {
    const plotW = W - PAD.left - PAD.right;
    const plotH = H - PAD.top - PAD.bottom;
    const weeks = impact.after_weekly;
    const maxY =
      Math.max(
        impact.before.precursor_rate,
        ...weeks.map((w) => w.precursor_rate),
        0.05
      ) * 1.15;
    const n = Math.max(1, weeks.length);
    const x = (i: number) => PAD.left + ((i + 1) / (n + 1)) * plotW;
    const y = (v: number) => PAD.top + plotH - (v / maxY) * plotH;
    return {
      plotW,
      plotH,
      maxY,
      beforeY: y(impact.before.precursor_rate),
      pts: weeks.map((w, i) => ({ ...w, cx: x(i), cy: y(w.precursor_rate) })),
      ticks: [0, maxY / 2, maxY].map((v) => ({ v, y: y(v) })),
    };
  }, [impact]);

  const line = model.pts
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.cx},${p.cy}`)
    .join(" ");

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full min-w-[480px]"
        role="img"
        aria-label={`Precursor rate: baseline ${impact.before.precursor_rate}, then ${impact.after_weekly.length} weekly readings after the intervention start date`}
      >
        <defs>
          <clipPath id={clipId}>
            <rect
              x={PAD.left}
              y={PAD.top}
              width={mounted ? model.plotW : 0}
              height={model.plotH}
              style={{ transition: "width 700ms ease" }}
            />
          </clipPath>
        </defs>

        {model.ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              y1={t.y}
              x2={W - PAD.right}
              y2={t.y}
              stroke="var(--line)"
              strokeOpacity={0.6}
            />
            <text
              x={PAD.left - 6}
              y={t.y + 3}
              textAnchor="end"
              className="fill-muted"
              style={{ fontSize: 10, fontVariantNumeric: "tabular-nums" }}
            >
              {t.v.toFixed(2)}
            </text>
          </g>
        ))}

        {/* baseline reference */}
        <line
          x1={PAD.left}
          y1={model.beforeY}
          x2={W - PAD.right}
          y2={model.beforeY}
          stroke="var(--neutral)"
          strokeWidth={1.5}
          strokeDasharray="5 3"
        />
        <text
          x={W - PAD.right}
          y={model.beforeY - 4}
          textAnchor="end"
          className="fill-muted"
          style={{ fontSize: 9 }}
        >
          baseline {impact.before.precursor_rate.toFixed(3)} ({impact.before.window_days}d)
        </text>

        <g clipPath={`url(#${clipId})`}>
          <path d={line} fill="none" stroke="var(--steel)" strokeWidth={2} />
          {model.pts.map((p) => (
            <g key={p.week}>
              <rect
                x={p.cx - 3}
                y={p.cy - 3}
                width={6}
                height={6}
                fill="var(--steel)"
                stroke="var(--surface)"
              >
                <title>{`Week ${p.week}: ${p.precursor_rate.toFixed(3)}`}</title>
              </rect>
              <text
                x={p.cx}
                y={H - PAD.bottom + 15}
                textAnchor="middle"
                className="fill-muted"
                style={{ fontSize: 9 }}
              >
                wk {p.week}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
