"use client";

import { Panel } from "@/components/ui/Panel";
import { Meter } from "@/components/ui/Meter";
import { confidenceBand, FIELD_META } from "@/lib/ontology";
import type { FieldRow } from "@/lib/report-fields";

/**
 * Per-field extraction readout. Hovering / focusing a row highlights that
 * field's marks in the report text; fields with no located span say so
 * plainly rather than pretending to a highlight.
 */
export function FieldConfidence({
  rows,
  activeField,
  onActivate,
}: {
  rows: FieldRow[];
  activeField: string | null;
  onActivate: (field: string | null) => void;
}) {
  return (
    <Panel title="Extracted fields">
      <ul className="divide-y divide-line">
        {rows.map((row) => {
          const band = confidenceBand(row.confidence);
          const color = FIELD_META[row.field]?.color ?? "#5a5f55";
          const isActive = activeField === row.field;
          return (
            <li key={row.field}>
              <button
                type="button"
                disabled={!row.located}
                onMouseEnter={() => row.located && onActivate(row.field)}
                onMouseLeave={() => onActivate(null)}
                onFocus={() => row.located && onActivate(row.field)}
                onBlur={() => onActivate(null)}
                className={`w-full py-2.5 text-left transition-colors ${
                  isActive ? "bg-panel" : ""
                } ${row.located ? "cursor-pointer" : "cursor-default"}`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-2 w-3 shrink-0"
                    style={{ backgroundColor: color }}
                    aria-hidden
                  />
                  <span className="label !text-ink">{row.label}</span>
                  <span className="tnum ml-auto text-xs text-muted">
                    {row.confidence.toFixed(2)}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-3 pl-5">
                  <Meter
                    value={row.confidence}
                    hue={band.hue}
                    label={`${row.label} confidence`}
                  />
                  <span className="text-2xs uppercase tracking-[0.06em] text-muted">
                    {band.label}
                  </span>
                </div>
                <p className="mt-1 pl-5 font-mono text-xs text-ink">
                  {row.value}
                </p>
                {!row.located && (
                  <p className="mt-0.5 pl-5 text-2xs italic text-muted">
                    Not located in the report text — label inferred by the model.
                  </p>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
