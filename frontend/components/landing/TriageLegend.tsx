import { Chip } from "@/components/ui/Chip";
import { BUCKET_LIST } from "./content";
import { Section } from "./Section";

export function TriageLegend() {
  return (
    <Section
      id="triage"
      index="03"
      eyebrow="Classification"
      title="Four buckets — two of them mean a human decides"
      lede="Colour does real work here, not decoration. The caution buckets are the review queue; the others are filed with their evidence trail."
    >
      <ul className="grid gap-px border border-line bg-line sm:grid-cols-2">
        {BUCKET_LIST.map((b) => (
          <li key={b.key} className="flex flex-col gap-2 bg-surface p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Chip hue={b.hue}>{b.label}</Chip>
              <span className="font-mono text-2xs text-muted">{b.key}</span>
            </div>
            <p className="text-xs text-muted">{b.blurb}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
