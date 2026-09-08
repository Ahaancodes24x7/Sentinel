"use client";

import { useEffect, useMemo, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { FIELD_META } from "@/lib/ontology";

export interface FieldSpan {
  field: string;
  span: [number, number];
  confidence: number;
}

interface Segment {
  start: number;
  end: number;
  text: string;
  fields: string[]; // fields covering this segment, in span order
  markIndex: number | null; // nth highlighted mark (for stagger), null if plain
}

function fieldColor(field: string): string {
  return FIELD_META[field]?.color ?? "#5a5f55";
}

function fieldLabel(field: string): string {
  return FIELD_META[field]?.label ?? field;
}

/**
 * Real span-highlighting renderer. Splits `text` at every span boundary so
 * overlapping spans render correctly (a char covered by two fields gets two
 * stacked underlines). This is NOT a keyword/regex highlighter — it works
 * purely from `[start, end]` character offsets into the original text.
 */
export function SpanText({
  text,
  spans,
  activeField,
}: {
  text: string;
  spans: FieldSpan[];
  activeField?: string | null;
}) {
  const reduce = useReducedMotion();

  // The one motion moment: highlights sweep in left-to-right, staggered.
  // Implemented as a CSS background-size transition (not clip-path) so it is
  // safe for marks that wrap across lines.
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    if (reduce) {
      setRevealed(true);
      return;
    }
    const raf = requestAnimationFrame(() => setRevealed(true));
    return () => cancelAnimationFrame(raf);
  }, [reduce]);

  const segments = useMemo<Segment[]>(() => {
    const valid = spans.filter(
      (s) =>
        Array.isArray(s.span) &&
        s.span[0] >= 0 &&
        s.span[1] <= text.length &&
        s.span[0] < s.span[1]
    );

    const boundaries = new Set<number>([0, text.length]);
    for (const s of valid) {
      boundaries.add(s.span[0]);
      boundaries.add(s.span[1]);
    }
    const points = [...boundaries].sort((a, b) => a - b);

    const segs: Segment[] = [];
    let markCounter = 0;
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i];
      const end = points[i + 1];
      if (start === end) continue;
      const fields = valid
        .filter((s) => s.span[0] <= start && s.span[1] >= end)
        .sort((a, b) => a.span[0] - b.span[0])
        .map((s) => s.field);
      segs.push({
        start,
        end,
        text: text.slice(start, end),
        fields,
        markIndex: fields.length ? markCounter++ : null,
      });
    }
    return segs;
  }, [text, spans]);

  return (
    <p className="whitespace-pre-wrap font-mono text-sm leading-7 text-ink">
      {segments.map((seg) => {
        if (!seg.fields.length) {
          return <span key={seg.start}>{seg.text}</span>;
        }

        const primary = seg.fields[0];
        const dimmed =
          activeField != null && !seg.fields.includes(activeField);
        const active =
          activeField != null && seg.fields.includes(activeField);

        // Layer 0 is the fill tint; layers 1..n are stacked underline bands,
        // one per covering field. All sweep from 0% to 100% width on reveal.
        const tint = active
          ? `${fieldColor(activeField!)}2e`
          : `${fieldColor(primary)}1f`;
        const layers = [
          `linear-gradient(${tint}, ${tint})`,
          ...seg.fields.map(
            (f) => `linear-gradient(${fieldColor(f)}, ${fieldColor(f)})`
          ),
        ];
        const widths = revealed ? "100%" : "0%";
        const sizes = [
          `${widths} 100%`,
          ...seg.fields.map(() => `${widths} 3px`),
        ];
        const positions = [
          "0 0",
          ...seg.fields.map((_, i) => `0 calc(100% - ${i * 4}px)`),
        ];
        const delayMs = reduce ? 0 : 120 + (seg.markIndex ?? 0) * 70;

        return (
          <mark
            key={seg.start}
            tabIndex={0}
            data-fields={seg.fields.join(" ")}
            aria-label={`${seg.fields.map(fieldLabel).join(", ")}: ${seg.text}`}
            title={seg.fields.map(fieldLabel).join(" · ")}
            className="rounded-none bg-transparent px-[1px] text-ink outline-offset-2"
            style={{
              backgroundImage: layers.join(", "),
              backgroundSize: sizes.join(", "),
              backgroundPosition: positions.join(", "),
              backgroundRepeat: "no-repeat",
              paddingBottom: `${seg.fields.length * 4}px`,
              filter: dimmed ? "grayscale(0.7) opacity(0.45)" : undefined,
              boxShadow: active
                ? `0 0 0 2px ${fieldColor(activeField!)}`
                : undefined,
              transition: `background-size 320ms ease ${delayMs}ms, filter 150ms ease, box-shadow 150ms ease`,
            }}
          >
            {seg.text}
          </mark>
        );
      })}
    </p>
  );
}

/** Legend for the fields present in a report. */
export function SpanLegend({
  fields,
  activeField,
  onHover,
}: {
  fields: string[];
  activeField?: string | null;
  onHover?: (field: string | null) => void;
}) {
  const seen = Array.from(new Set(fields));
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1">
      {seen.map((f) => (
        <li key={f}>
          <button
            type="button"
            onMouseEnter={() => onHover?.(f)}
            onMouseLeave={() => onHover?.(null)}
            onFocus={() => onHover?.(f)}
            onBlur={() => onHover?.(null)}
            className={`flex items-center gap-1.5 text-2xs uppercase tracking-[0.06em] ${
              activeField === f ? "text-ink" : "text-muted"
            }`}
          >
            <span
              className="inline-block h-2 w-4"
              style={{ backgroundColor: fieldColor(f) }}
            />
            {fieldLabel(f)}
          </button>
        </li>
      ))}
    </ul>
  );
}
