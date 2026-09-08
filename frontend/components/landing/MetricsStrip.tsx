import { METRICS } from "./content";

export function MetricsStrip() {
  return (
    <section className="border-y border-line bg-surface">
      <dl className="mx-auto grid max-w-[1100px] grid-cols-2 gap-px bg-line sm:grid-cols-4">
        {METRICS.map((m) => (
          <div key={m.label} className="bg-surface px-4 py-6 text-center">
            <dt className="sr-only">{m.label}</dt>
            <dd className="tnum text-xl font-bold text-ink">{m.value}</dd>
            <p className="label mt-1">{m.label}</p>
          </div>
        ))}
      </dl>
    </section>
  );
}
