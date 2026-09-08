import { CAPABILITIES } from "./content";
import { Section } from "./Section";

export function CapabilityGrid() {
  return (
    <Section
      id="capabilities"
      index="02"
      eyebrow="Console"
      title="One console for the whole HSE review loop"
      lede="Every screen is role-gated from a single capability matrix — nothing is hidden with CSS."
    >
      <div className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {CAPABILITIES.map((c) => (
          <article key={c.title} className="flex flex-col gap-2 bg-surface p-5">
            <div className="flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-bold text-ink">{c.title}</h3>
              <span className="shrink-0 font-mono text-2xs text-muted">
                {c.tag}
              </span>
            </div>
            <p className="text-xs text-muted">{c.detail}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
