import { motion } from 'framer-motion';
import { Chip, Counter, PulseDot, ScanPanel } from '../components/kinetic';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { useOntology, useReports } from '../api/hooks';

export function LifeSavingRulesPage() {
  const { data: ontology, isLoading, error } = useOntology();
  const { data: reports } = useReports({ sif_potential: true, limit: 200 });

  const rules = Object.entries(ontology?.life_saving_rules ?? {});
  const energyTypes = Object.entries(ontology?.energy_types ?? {});

  const counts = new Map<string, number>();
  (reports?.items ?? []).forEach((r) => {
    if (r.lsr_tag && r.lsr_tag !== 'N/A') {
      counts.set(r.lsr_tag, (counts.get(r.lsr_tag) ?? 0) + 1);
    }
  });
  const max = Math.max(...Array.from(counts.values()), 1);

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="info" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">
            REQUIREMENT (B) · RULE TAGGING
          </span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Life-Saving Rules</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          IOGP Report 459. Rule assignment is an{' '}
          <strong className="text-ink-2">ontology lookup</strong> from the extracted energy type,
          not a learned end-to-end mapping — so the logic is inspectable line by line and never
          drifts with a model update.
        </p>
      </div>

      {isLoading ? (
        <ScanPanel>
          <PanelLoading rows={6} />
        </ScanPanel>
      ) : error ? (
        <QueryError error={error} />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rules.map(([name, def], i) => {
            const mapped = energyTypes.filter(([, e]) => e.lsr_tag === name);
            const count = counts.get(name) ?? 0;
            return (
              <motion.div
                key={name}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <ScanPanel className="h-full p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="text-base leading-tight text-ink">{name}</h2>
                    <span className="font-display text-2xl text-hivis">
                      <Counter value={count} />
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink-3">{def.description}</p>

                  <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-surface-3">
                    <motion.div
                      className="h-full rounded-full bg-hivis"
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / max) * 100}%` }}
                      transition={{ delay: 0.2 + i * 0.04, duration: 0.7 }}
                    />
                  </div>

                  <div className="mt-3 font-mono text-[9px] tracked text-ink-4">
                    MAPPED ENERGY TYPES
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {mapped.map(([et, meta]) => (
                      <Chip key={et} tone={meta.is_high_energy ? 'critical' : 'neutral'}>
                        {et}
                      </Chip>
                    ))}
                  </div>
                </ScanPanel>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
