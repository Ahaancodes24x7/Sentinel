import { motion } from 'framer-motion';
import { ShieldOff } from 'lucide-react';
import { Bar, Chip, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useBarrierFailures, useOntology } from '../api/hooks';
import { cn } from '../lib/cn';
import { ALL_SITES, useSelectedSite } from '../lib/siteContext';

export function BarrierFailuresPage() {
  const { selectedSite } = useSelectedSite();
  const siteParam = selectedSite.site_id !== ALL_SITES.site_id ? selectedSite.site_id : undefined;
  const { data, isLoading, error } = useBarrierFailures(siteParam);
  const { data: ontology } = useOntology();
  const items = data?.items ?? [];
  const barrierTypes = Object.entries(ontology?.barrier_types ?? {});

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="high" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">
            BARRIER FAILURE AS THE CORE SIGNAL ·{' '}
            {siteParam ? selectedSite.canonical_name.toUpperCase() : 'ALL SITES'}
          </span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Barrier Failures</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          Which safety-critical barriers keep degrading, and during which activity. This is the leap
          from &ldquo;Rig 4 has the most reports&rdquo; to something an HSE manager can act on.
        </p>
      </div>

      <ScanPanel>
        <PanelHead
          title="ACTIVITY × FAILURE MODE"
          sub="Ranked by SIF-flagged report count"
          tone="high"
          right={<Chip tone="neutral">{items.length} PAIRS</Chip>}
        />
        {isLoading ? (
          <PanelLoading rows={8} />
        ) : error ? (
          <QueryError error={error} />
        ) : items.length === 0 ? (
          <EmptyPanel icon={ShieldOff} title="No barrier failures recorded" />
        ) : (
          <div className="divide-y divide-line-faint">
            {items.slice(0, 24).map((row, i) => (
              <motion.div
                key={`${row.activity}-${row.barrier_failure_mode}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.4) }}
                className="px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm text-ink">{row.barrier_failure_mode}</div>
                    <div className="truncate font-mono text-2xs text-ink-4">{row.activity}</div>
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-2xs tabular text-ink-3">
                      {row.sif_count}/{row.report_count}
                    </span>
                    <span
                      className={cn(
                        'font-display text-xl',
                        row.sif_share > 0.8
                          ? 'text-critical'
                          : row.sif_share > 0.5
                            ? 'text-high'
                            : 'text-medium',
                      )}
                    >
                      {(row.sif_share * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <Bar
                  value={row.sif_share}
                  tone={row.sif_share > 0.8 ? 'critical' : row.sif_share > 0.5 ? 'high' : 'medium'}
                  className="mt-2"
                  delay={i * 0.02}
                />
              </motion.div>
            ))}
          </div>
        )}
      </ScanPanel>

      <ScanPanel>
        <PanelHead
          title="BARRIER ONTOLOGY"
          sub="Bow-tie vocabulary, flattened to report level"
          tone="info"
        />
        <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
          {barrierTypes.map(([name, def], i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-md border border-line bg-surface-2 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm text-ink">{name}</span>
                <Chip tone={def.is_direct_control ? 'low' : 'medium'}>
                  {def.is_direct_control ? 'DIRECT' : 'INDIRECT'}
                </Chip>
              </div>
              <div className="mt-1 font-mono text-2xs tracked text-ink-4">
                {def.control_level.toUpperCase()}
              </div>
              <ul className="mt-2 space-y-0.5">
                {def.failure_modes.slice(0, 4).map((m) => (
                  <li key={m} className="flex items-start gap-1.5 text-2xs text-ink-3">
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-high" />
                    {m}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
        <div className="border-t border-line px-4 py-2.5">
          <p className="text-2xs text-ink-4">
            A <strong className="text-ink-3">direct</strong> control stays effective under
            foreseeable human error (a mechanical barrier). An{' '}
            <strong className="text-ink-3">indirect</strong> one — a permit, a plan — does not,
            which is why a confirmed permit alone does not clear a high-energy exposure in the SCL
            decision.
          </p>
        </div>
      </ScanPanel>
    </div>
  );
}
