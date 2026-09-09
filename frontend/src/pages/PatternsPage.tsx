import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GitBranch, Link2, TriangleAlert } from 'lucide-react';
import {
  Bar,
  Chip,
  Counter,
  PanelHead,
  PulseDot,
  ScanPanel,
  type Tone,
} from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useAssociations, useClusters } from '../api/hooks';
import type { ClusterItem } from '../api/types';
import { cn } from '../lib/cn';

const PATTERN_TONE: Record<string, Tone> = {
  established: 'high',
  emerging: 'critical',
  sporadic_high_severity: 'medium',
};

const PATTERN_COPY: Record<string, string> = {
  established: 'Recurring across the whole window',
  emerging: 'Concentrated in the most recent weeks',
  sporadic_high_severity: 'Rare, but high energy with no barrier',
};

/**
 * Force-free cluster map.
 *
 * Deliberately not a physics simulation: clusters are laid out on a stable
 * radial grid ordered by size, so the same corpus always produces the same
 * picture. A jittering force graph looks impressive and makes it impossible to
 * say "that cluster grew" between two runs.
 */
function ClusterMap({
  clusters,
  selected,
  onSelect,
}: {
  clusters: ClusterItem[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const nodes = useMemo(() => {
    const top = [...clusters].sort((a, b) => b.member_count - a.member_count).slice(0, 24);
    const maxCount = Math.max(...top.map((c) => c.member_count), 1);
    return top.map((c, i) => {
      const ring = i < 1 ? 0 : i < 7 ? 1 : i < 15 ? 2 : 3;
      const inRing = ring === 0 ? 1 : ring === 1 ? 6 : ring === 2 ? 8 : 9;
      const idxInRing = ring === 0 ? 0 : ring === 1 ? i - 1 : ring === 2 ? i - 7 : i - 15;
      const angle = (idxInRing / inRing) * Math.PI * 2 - Math.PI / 2;
      const radius = ring * 26;
      return {
        cluster: c,
        x: 50 + Math.cos(angle) * radius,
        y: 50 + Math.sin(angle) * radius * 0.82,
        r: 3 + (c.member_count / maxCount) * 9,
      };
    });
  }, [clusters]);

  return (
    <svg viewBox="0 0 100 100" className="h-full w-full" aria-label="Precursor cluster map">
      {/* concentric guides */}
      {[26, 52, 78].map((r) => (
        <ellipse
          key={r}
          cx="50"
          cy="50"
          rx={r}
          ry={r * 0.82}
          fill="none"
          stroke="var(--color-chart-grid)"
          strokeWidth="0.2"
          strokeDasharray="1 1.5"
        />
      ))}

      {nodes.map((n, i) => {
        const tone = PATTERN_TONE[n.cluster.pattern_type] ?? 'hivis';
        const isSel = selected === n.cluster.cluster_id;
        return (
          <g
            key={n.cluster.cluster_id}
            onClick={() => onSelect(n.cluster.cluster_id)}
            className="cursor-pointer"
          >
            <motion.circle
              cx={n.x}
              cy={n.y}
              initial={{ r: 0, opacity: 0 }}
              animate={{ r: n.r, opacity: isSel ? 1 : 0.72 }}
              transition={{ delay: i * 0.03, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              fill={`var(--color-${tone})`}
              fillOpacity={isSel ? 0.35 : 0.16}
              stroke={`var(--color-${tone})`}
              strokeWidth={isSel ? 0.8 : 0.4}
            />
            {n.cluster.pattern_type === 'emerging' && (
              <circle
                cx={n.x}
                cy={n.y}
                r={n.r}
                fill="none"
                stroke="var(--color-critical)"
                strokeWidth="0.3"
                opacity="0.6"
              >
                <animate
                  attributeName="r"
                  values={`${n.r};${n.r * 1.8};${n.r}`}
                  dur="2.4s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.6;0;0.6"
                  dur="2.4s"
                  repeatCount="indefinite"
                />
              </circle>
            )}
            <text
              x={n.x}
              y={n.y + 0.9}
              textAnchor="middle"
              className="pointer-events-none"
              style={{ fontSize: '2.4px', fill: 'var(--color-ink)', fontFamily: 'var(--font-mono)' }}
            >
              {n.cluster.member_count}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* -------------------------------------------------------------------------- */

export function PatternsPage() {
  const { data, isLoading, error } = useClusters(undefined, 3);
  const { data: assoc } = useAssociations(undefined, 12);
  const [selected, setSelected] = useState<string | null>(null);

  const clusters = data?.clusters ?? [];
  const selectedCluster = clusters.find((c) => c.cluster_id === selected) ?? clusters[0];

  const emerging = clusters.filter((c) => c.pattern_type === 'emerging');
  const sporadic = clusters.filter((c) => c.pattern_type === 'sporadic_high_severity');

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="violet" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">
            REQUIREMENT (C) · PATTERN DISCOVERY
          </span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Precursor Patterns</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          Clustered over the <strong className="text-ink-2">structured event frame</strong>, not
          raw text — so “stood under the load” and “was positioned beneath the suspended pipe
          section” land in the same pattern despite sharing almost no vocabulary.
        </p>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox label="CLUSTERS" value={clusters.length} tone="hivis" />
        <StatBox label="EMERGING" value={emerging.length} tone="critical" />
        <StatBox label="RARE & SEVERE" value={sporadic.length} tone="medium" />
        <StatBox label="UNCLUSTERED" value={data?.noise_count ?? 0} tone="neutral" />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
        {/* Map */}
        <ScanPanel className="lg:col-span-3">
          <PanelHead
            title="CLUSTER MAP"
            sub="Radius = report count · pulsing ring = emerging"
            tone="violet"
            right={
              data?.computed_at ? (
                <span className="font-mono text-2xs text-ink-4">
                  batch {data.computed_at.slice(0, 16).replace('T', ' ')}
                </span>
              ) : undefined
            }
          />
          <div className="h-[26rem] p-3">
            {isLoading ? (
              <PanelLoading rows={6} />
            ) : error ? (
              <QueryError error={error} />
            ) : clusters.length === 0 ? (
              <EmptyPanel
                icon={GitBranch}
                title="No clusters yet"
                message="Press RECOMPUTE in the top bar to run the batch clustering job."
              />
            ) : (
              <ClusterMap
                clusters={clusters}
                selected={selectedCluster?.cluster_id ?? null}
                onSelect={setSelected}
              />
            )}
          </div>
        </ScanPanel>

        {/* Selected cluster */}
        <ScanPanel className="lg:col-span-2">
          <PanelHead title="PATTERN DETAIL" tone="critical" />
          {!selectedCluster ? (
            <EmptyPanel title="Select a cluster" />
          ) : (
            <div className="space-y-3 p-4">
              <div className="flex flex-wrap items-center gap-1.5">
                <Chip tone={PATTERN_TONE[selectedCluster.pattern_type] ?? 'neutral'} dot>
                  {selectedCluster.pattern_type.replace(/_/g, ' ').toUpperCase()}
                </Chip>
                <Chip tone="neutral">{selectedCluster.cluster_id}</Chip>
              </div>

              <p className="text-xs text-ink-4">
                {PATTERN_COPY[selectedCluster.pattern_type]}
              </p>

              <div className="rounded-md border border-line bg-surface-2 p-3">
                <div className="font-mono text-[9px] tracked text-ink-4">PATTERN SIGNATURE</div>
                <div className="mt-1 text-sm leading-relaxed text-ink">
                  {selectedCluster.pattern_summary}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <MiniStat label="REPORTS" value={selectedCluster.member_count} />
                <MiniStat label="SITES" value={selectedCluster.site_count} />
              </div>

              <div>
                <div className="flex justify-between font-mono text-2xs text-ink-4">
                  <span>SIF SHARE</span>
                  <span className="tabular text-ink-2">
                    {(selectedCluster.sif_share * 100).toFixed(0)}%
                  </span>
                </div>
                <Bar value={selectedCluster.sif_share} tone="critical" className="mt-1" />
              </div>

              {selectedCluster.primary_barrier_failure && (
                <div>
                  <div className="font-mono text-[9px] tracked text-ink-4">
                    DOMINANT BARRIER FAILURE
                  </div>
                  <div className="mt-0.5 text-sm text-high">
                    {selectedCluster.primary_barrier_failure}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-1">
                {selectedCluster.sites.slice(0, 8).map((s) => (
                  <Chip key={s} tone="neutral">
                    {s}
                  </Chip>
                ))}
              </div>

              <div className="flex items-center justify-between border-t border-line pt-3">
                <span className="font-mono text-2xs text-ink-4">
                  {selectedCluster.first_seen?.slice(0, 10)} →{' '}
                  {selectedCluster.last_seen?.slice(0, 10)}
                </span>
                <Link
                  to={`/recommendations?pattern=${selectedCluster.cluster_id}`}
                  className="font-mono text-2xs tracked text-hivis hover:underline"
                >
                  INTERVENTIONS →
                </Link>
              </div>
            </div>
          )}
        </ScanPanel>
      </div>

      {/* Association rules */}
      <ScanPanel>
        <PanelHead
          title="CO-OCCURRENCE RULES"
          sub="Combinations that are individually unremarkable but jointly dangerous"
          tone="info"
          right={<Chip tone="info">{assoc?.rules?.length ?? 0} RULES</Chip>}
        />
        {!assoc ? (
          <PanelLoading rows={5} />
        ) : assoc.rules.length === 0 ? (
          <EmptyPanel icon={Link2} title="No rules above threshold" />
        ) : (
          <div className="divide-y divide-line-faint">
            {assoc.rules.map((rule, i) => (
              <motion.div
                key={`${rule.antecedent_text}-${rule.consequent_text}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-start gap-3 px-4 py-3"
              >
                <div
                  className={cn(
                    'mt-0.5 flex h-8 w-12 shrink-0 flex-col items-center justify-center rounded-sm border font-mono',
                    rule.lift >= 3
                      ? 'border-critical-edge bg-critical-wash text-critical'
                      : rule.lift >= 2
                        ? 'border-high-edge bg-high-wash text-high'
                        : 'border-line-bright bg-surface-2 text-ink-2',
                  )}
                >
                  <span className="text-xs tabular leading-none">{rule.lift.toFixed(1)}×</span>
                  <span className="text-[8px] tracked leading-none opacity-70">LIFT</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink-2">{rule.statement}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-2xs text-ink-4">
                    <span>{rule.report_count} reports</span>
                    <span>·</span>
                    <span>confidence {(rule.confidence * 100).toFixed(0)}%</span>
                    <span>·</span>
                    <span>baseline {(rule.baseline * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
        <div className="flex items-start gap-2 border-t border-line px-4 py-2.5">
          <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0 text-medium" strokeWidth={2} />
          <p className="text-2xs text-ink-4">{assoc?.note}</p>
        </div>
      </ScanPanel>
    </div>
  );
}

function StatBox({ label, value, tone }: { label: string; value: number; tone: Tone }) {
  return (
    <ScanPanel className="p-3">
      <div className="flex items-center gap-1.5">
        <PulseDot tone={tone} size={5} live={tone === 'critical'} />
        <span className="font-mono text-[9px] tracked text-ink-4">{label}</span>
      </div>
      <div className="mt-1 font-display text-3xl text-ink">
        <Counter value={value} />
      </div>
    </ScanPanel>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 px-2.5 py-2">
      <div className="font-mono text-[9px] tracked text-ink-4">{label}</div>
      <div className="font-mono text-lg tabular text-ink">{value}</div>
    </div>
  );
}
