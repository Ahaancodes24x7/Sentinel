"use client";

import { useId, useMemo } from "react";
import { useMounted } from "@/lib/use-mounted";
import type { TrendPoint, TrendAlert } from "@/lib/api/schemas";

const W = 760;
const H = 300;
const PAD = { top: 16, right: 16, bottom: 44, left: 40 };

/**
 * Hand-rolled trend chart (SVG), control-room-readout styled: hairline
 * gridlines, tabular-nums axis labels, square markers. Alert periods get a
 * caution marker; the alert's own `message` + `method` are surfaced verbatim
 * (aria-label here, and a verbatim list beside the chart on the page).
 */
export function TrendChart({
  series,
  alerts,
  granularity,
}: {
  series: TrendPoint[];
  alerts: TrendAlert[];
  granularity: string;
}) {
  const mounted = useMounted();
  const clipId = useId();

  const { pts, ticks, maxY, plotW, plotH, alertX } = useMemo(() => {
    const plotW = W - PAD.left - PAD.right;
    const plotH = H - PAD.top - PAD.bottom;
    const maxRaw = Math.max(1, ...series.map((s) => s.count));
    const maxY = niceMax(maxRaw);
    const n = Math.max(1, series.length - 1);
    const x = (i: number) => PAD.left + (i / n) * plotW;
    const y = (v: number) => PAD.top + plotH - (v / maxY) * plotH;

    const pts = series.map((s, i) => ({
      ...s,
      cx: x(i),
      cy: y(s.count),
      i,
    }));
    const ticks = tickValues(maxY).map((t) => ({ v: t, y: y(t) }));
    const alertX = new Map<string, number>();
    alerts.forEach((a) => {
      const idx = series.findIndex((s) => s.period === a.period);
      if (idx >= 0) alertX.set(a.period, x(idx));
    });
    return { pts, ticks, maxY, plotW, plotH, alertX };
  }, [series, alerts]);

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.cx},${p.cy}`).join(" ");
  const areaPath =
    pts.length > 0
      ? `${linePath} L${pts[pts.length - 1].cx},${PAD.top + plotH} L${pts[0].cx},${PAD.top + plotH} Z`
      : "";

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full min-w-[560px]"
        role="img"
        aria-label={`Precursor count by ${granularity} period, ${series.length} periods, ${alerts.length} alert${alerts.length === 1 ? "" : "s"}`}
      >
        <defs>
          <clipPath id={clipId}>
            <rect
              x={PAD.left}
              y={PAD.top}
              width={mounted ? plotW : 0}
              height={plotH}
              style={{ transition: "width 700ms ease" }}
            />
          </clipPath>
        </defs>

        {/* gridlines + y labels */}
        {ticks.map((t) => (
          <g key={t.v}>
            <line
              x1={PAD.left}
              y1={t.y}
              x2={W - PAD.right}
              y2={t.y}
              stroke="var(--line)"
              strokeWidth={t.v === 0 ? 1.5 : 1}
              strokeOpacity={t.v === 0 ? 1 : 0.6}
            />
            <text
              x={PAD.left - 6}
              y={t.y + 3}
              textAnchor="end"
              className="fill-muted"
              style={{ fontSize: 10, fontVariantNumeric: "tabular-nums" }}
            >
              {t.v}
            </text>
          </g>
        ))}

        {/* x labels */}
        {pts.map((p) =>
          p.i % Math.ceil(pts.length / 8 || 1) === 0 ? (
            <text
              key={p.period}
              x={p.cx}
              y={H - PAD.bottom + 16}
              textAnchor="middle"
              className="fill-muted"
              style={{ fontSize: 9, fontVariantNumeric: "tabular-nums" }}
            >
              {p.period.slice(5)}
            </text>
          ) : null
        )}

        {/* alert markers */}
        {[...alertX.entries()].map(([period, cx]) => {
          const a = alerts.find((al) => al.period === period)!;
          return (
            <g
              key={period}
              tabIndex={0}
              role="img"
              aria-label={`Alert at ${period} (${a.method}): ${a.message}`}
              className="outline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
            >
              <title>{`${a.method} · ${period}: ${a.message}`}</title>
              <line
                x1={cx}
                y1={PAD.top}
                x2={cx}
                y2={PAD.top + plotH}
                stroke="var(--caution)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
              />
              <path
                d={`M${cx},${PAD.top - 2} l-5,-9 l10,0 Z`}
                fill="var(--caution)"
              />
            </g>
          );
        })}

        <g clipPath={`url(#${clipId})`}>
          <path d={areaPath} fill="var(--steel)" fillOpacity={0.1} />
          <path
            d={linePath}
            fill="none"
            stroke="var(--steel)"
            strokeWidth={2}
          />
          {pts.map((p) => {
            const isAlert = alertX.has(p.period);
            return (
              <rect
                key={p.period}
                x={p.cx - 3}
                y={p.cy - 3}
                width={6}
                height={6}
                fill={isAlert ? "var(--caution)" : "var(--steel)"}
                stroke="var(--surface)"
                strokeWidth={1}
              >
                <title>{`${p.period}: ${p.count}`}</title>
              </rect>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function niceMax(v: number): number {
  if (v <= 5) return 5;
  if (v <= 10) return 10;
  if (v <= 20) return 20;
  return Math.ceil(v / 10) * 10;
}

function tickValues(maxY: number): number[] {
  const step = maxY / 4;
  return [0, 1, 2, 3, 4].map((i) => Math.round(i * step));
}
