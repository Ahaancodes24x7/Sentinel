import { PIPELINE, PIPELINE_LOOP } from "./content";
import { Section } from "./Section";

export function PipelineStrip() {
  return (
    <Section
      id="pipeline"
      index="01"
      eyebrow="How it works"
      title="From raw report to ranked intervention"
      lede="Every report runs the full pipeline. Nothing is auto-actioned above a human's head — confidence routing decides only what needs a reviewer."
    >
      <ol className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {PIPELINE.map((s) => (
          <li key={s.step} className="flex flex-col gap-2 bg-surface p-4">
            <div className="flex items-center gap-2">
              <span className="tnum text-2xs font-semibold text-focus">
                {s.step}
              </span>
              <span className="label !text-ink">{s.name}</span>
            </div>
            <p className="text-xs text-muted">{s.detail}</p>
          </li>
        ))}
        <li className="flex flex-col gap-2 bg-panel p-4">
          <span className="label !text-focus">Loop</span>
          <p className="text-xs text-muted">{PIPELINE_LOOP}</p>
        </li>
      </ol>
    </Section>
  );
}
