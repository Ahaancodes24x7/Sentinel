/**
 * Normalises the (intentionally messy) `extracted_fields` payload into:
 *  - `spans`   : FieldSpan[] for the SpanText highlighter (only fields with a
 *                valid [start,end] and matching substring)
 *  - `rows`    : one display row per field, with confidence + located flag
 *  - `hazardIssue` : set when `hazard` arrived in the buggy pipeline shape
 *                    ({label,...} instead of {text, span}) — the known backend bug
 */
import type { ExtractedFields } from "./api/schemas";
import { humanLabel } from "./ontology";
import type { FieldSpan } from "@/components/report/SpanText";

export interface FieldRow {
  field: string;
  label: string;
  value: string;
  confidence: number;
  located: boolean;
}

export interface NormalizedFields {
  spans: FieldSpan[];
  rows: FieldRow[];
  hazardIssue: string | null;
}

function isValidSpan(
  span: unknown,
  textLen: number
): span is [number, number] {
  return (
    Array.isArray(span) &&
    span.length === 2 &&
    typeof span[0] === "number" &&
    typeof span[1] === "number" &&
    span[0] >= 0 &&
    span[1] <= textLen &&
    span[0] < span[1]
  );
}

export function normalizeFields(
  ef: ExtractedFields,
  reportText: string
): NormalizedFields {
  const spans: FieldSpan[] = [];
  const rows: FieldRow[] = [];
  let hazardIssue: string | null = null;

  const pushSpan = (field: string, span: [number, number], confidence: number) => {
    spans.push({ field, span, confidence });
  };

  // activity — span field
  {
    const a = ef.activity;
    const located = isValidSpan(a?.span, reportText.length);
    if (located) pushSpan("activity", a.span as [number, number], a.confidence);
    rows.push({
      field: "activity",
      label: "Activity",
      value: a?.text ?? "—",
      confidence: a?.confidence ?? 0,
      located,
    });
  }

  // hazard — nullable span field OR the buggy {label,...} shape
  if (ef.hazard) {
    const h = ef.hazard as Record<string, unknown>;
    const hasText = typeof h.text === "string";
    const located = isValidSpan(h.span, reportText.length);
    if (hasText && located) {
      pushSpan("hazard", h.span as [number, number], Number(h.confidence) || 0);
    }
    if (!hasText && typeof h.label === "string") {
      hazardIssue =
        "Hazard evidence arrived in the pipeline's raw shape ({best_category, matches}) rather than the {text, span, confidence} contract, so it can't be highlighted in the report text. Backend integration issue.";
    }
    rows.push({
      field: "hazard",
      label: "Hazard",
      value: hasText
        ? String(h.text)
        : typeof h.label === "string"
          ? humanLabel(h.label)
          : "—",
      confidence: Number(h.confidence) || 0,
      located: hasText && located,
    });
  }

  // energy_type — label field
  {
    const e = ef.energy_type;
    const located = isValidSpan(e?.span, reportText.length);
    if (located) pushSpan("energy_type", e.span as [number, number], e.confidence);
    rows.push({
      field: "energy_type",
      label: "Energy type",
      value: humanLabel(e?.label),
      confidence: e?.confidence ?? 0,
      located,
    });
  }

  // exposure — label field
  {
    const x = ef.exposure;
    const located = isValidSpan(x?.span, reportText.length);
    if (located) pushSpan("exposure", x.span as [number, number], x.confidence);
    rows.push({
      field: "exposure",
      label: "Exposure",
      value: humanLabel(x?.label),
      confidence: x?.confidence ?? 0,
      located,
    });
  }

  // barrier — nullable span field
  if (ef.barrier) {
    const b = ef.barrier;
    const located = isValidSpan(b.span, reportText.length);
    if (located) pushSpan("barrier", b.span as [number, number], b.confidence);
    rows.push({
      field: "barrier",
      label: "Barrier",
      value: b.text ?? "—",
      confidence: b.confidence ?? 0,
      located,
    });
  }

  // barrier_status — label field
  {
    const bs = ef.barrier_status;
    const located = isValidSpan(bs?.span, reportText.length);
    if (located)
      pushSpan("barrier_status", bs.span as [number, number], bs.confidence);
    rows.push({
      field: "barrier_status",
      label: "Barrier status",
      value: humanLabel(bs?.label),
      confidence: bs?.confidence ?? 0,
      located,
    });
  }

  // location — nullable span field
  if (ef.location) {
    const l = ef.location;
    const located = isValidSpan(l.span, reportText.length);
    if (located) pushSpan("location", l.span as [number, number], l.confidence);
    rows.push({
      field: "location",
      label: "Location",
      value: l.text ?? "—",
      confidence: l.confidence ?? 0,
      located,
    });
  }

  return { spans, rows, hazardIssue };
}
