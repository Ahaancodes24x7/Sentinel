/**
 * Tiny helper so mock report text and character spans can never drift apart.
 * Write the report with `{{field:substring}}` markers; the builder strips the
 * markers and returns the clean text plus exact [start, end] offsets into it.
 * Overlapping / nested markers are supported by writing them adjacently.
 */
export interface BuiltSpan {
  field: string;
  text: string;
  span: [number, number];
  confidence: number;
}

const MARK = /\{\{([a-z_]+)(?::([0-9.]+))?\|([^{}]*)\}\}/;

export function buildReport(
  template: string,
  confidences: Record<string, number> = {}
): { text: string; spans: BuiltSpan[] } {
  let text = template;
  const spans: BuiltSpan[] = [];
  let m: RegExpExecArray | null;

  // Resolve markers left-to-right, rebuilding indices each pass.
  while ((m = MARK.exec(text))) {
    const [full, field, confRaw, inner] = m;
    const start = m.index;
    text = text.slice(0, start) + inner + text.slice(start + full.length);
    spans.push({
      field,
      text: inner,
      span: [start, start + inner.length],
      confidence: confRaw
        ? Number(confRaw)
        : confidences[field] ?? 0.8,
    });
  }

  spans.sort((a, b) => a.span[0] - b.span[0]);
  return { text, spans };
}

export function spanOf(
  spans: BuiltSpan[],
  field: string
): [number, number] | null {
  return spans.find((s) => s.field === field)?.span ?? null;
}
