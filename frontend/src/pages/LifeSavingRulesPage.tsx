import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  ArrowUpFromLine,
  Box,
  ClipboardCheck,
  Construction,
  Crosshair,
  Flame,
  ShieldCheck,
  ShieldOff,
  TriangleAlert,
  Truck,
  Zap,
  ZapOff,
  type LucideIcon,
} from 'lucide-react';
import { Bar, Chip, Counter, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { Hint } from '../components/common/Hint';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { useOntology, useReports } from '../api/hooks';
import type { Ontology, OntologyEnergyType } from '../api/types';
import { cn } from '../lib/cn';

/** Ontology icon slugs -> concrete glyphs. Falls back to ShieldOff for any
 *  future rule added to the taxonomy without an icon this page knows yet. */
const RULE_ICONS: Record<string, LucideIcon> = {
  'shield-off': ShieldOff,
  box: Box,
  truck: Truck,
  'zap-off': ZapOff,
  flame: Flame,
  crosshair: Crosshair,
  crane: Construction,
  'clipboard-check': ClipboardCheck,
  'arrow-up-from-line': ArrowUpFromLine,
};

/**
 * Why each rule exists, in plain language — the ontology's one-line
 * `description` (e.g. "Obtain authorisation before entering a confined
 * space.") states WHAT the rule requires; this states WHY that requirement
 * is the one that actually prevents a fatality, which is the part a reviewer
 * unfamiliar with IOGP Report 459 has no way to infer from the label alone.
 * Static reference content, not derived from any report in this corpus.
 */
const RULE_KNOWLEDGE: Record<string, string> = {
  'Bypassing Safety Controls':
    'Interlocks, alarms and trip systems exist so a single human mistake cannot, by itself, cause a major accident. Disabling or overriding one — even briefly, even with good intentions — removes exactly the barrier meant to catch that mistake, often without anyone else realising it happened.',
  'Confined Space':
    'A confined space can kill through an atmosphere that looks and smells completely normal — oxygen deficiency, a toxic gas, or a flammable build-up are all invisible without testing. Authorisation first means the atmosphere has actually been tested, ventilation or monitoring is running, and someone outside knows you are in there.',
  Driving:
    'Vehicles cause more injuries on an industrial site than almost any other single hazard, precisely because they are familiar and therefore under-respected. This rule is the basics everyone already knows — seatbelt, speed limit, fitness to drive, no phone — because incident data keeps showing people skip them under time pressure.',
  'Energy Isolation':
    'Verified isolation is the difference between "the power is probably off" and "it is off, tested, and cannot come back on while I am working." Trapped hydraulic pressure, a re-energised circuit, or a valve someone reopens mid-job are common, ordinary ways this rule gets violated — and each is directly fatal.',
  'Hot Work':
    'An open flame, a spark or a hot surface only becomes a fire or explosion in the presence of something that can burn. This rule is about verifying — not assuming — that the atmosphere is free of flammable vapour and ignition sources stay controlled for as long as the work continues, not just at the start.',
  'Line of Fire':
    'Stored energy that releases — a cable snapping under tension, a dropped tool, a pressurised line — travels in a straight line and does not care who is standing in it. This rule is about not being in that path, which is a physical position, not a hope.',
  'Safe Mechanical Lifting':
    'A suspended load carries more stored energy than almost anything else on an industrial site, and it fails without warning. Planning the lift, keeping the load path clear, and never standing under a suspended load is the entire content of this rule, because that is what actually prevents a crush fatality.',
  'Work Authorisation':
    'A permit is not paperwork — it is the record that someone with the authority and the full site picture, not just the crew doing the job, checked the scope against actual site conditions before work started. A verbal go-ahead skips that check.',
  'Working at Height':
    'A fall from height is fatal at heights most people do not intuitively expect, and an unclipped harness is invisible right up until it matters. This rule is about fall protection being in place and used correctly for the entire time someone is exposed, not just when a supervisor happens to be watching.',
};

const toRad = (deg: number) => (deg * Math.PI) / 180;
function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  return [cx + r * Math.cos(toRad(deg)), cy + r * Math.sin(toRad(deg))];
}
function wedgePath(cx: number, cy: number, rOuter: number, rInner: number, a0: number, a1: number) {
  const [x1, y1] = polar(cx, cy, rOuter, a0);
  const [x2, y2] = polar(cx, cy, rOuter, a1);
  const [x3, y3] = polar(cx, cy, rInner, a1);
  const [x4, y4] = polar(cx, cy, rInner, a0);
  const large = a1 - a0 > 180 ? 1 : 0;
  return [
    `M ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`,
    `L ${x3.toFixed(2)} ${y3.toFixed(2)}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${x4.toFixed(2)} ${y4.toFixed(2)}`,
    'Z',
  ].join(' ');
}

interface RankedRule {
  name: string;
  icon?: string;
  description?: string;
  count: number;
  energies: [string, OntologyEnergyType][];
  barriers: [string, NonNullable<Ontology['barrier_types']>[string]][];
  failureModes: string[];
  highEnergyCount: number;
  directBarrierCount: number;
}

/**
 * Deterministic radial "energy wheel" — same visual language as the cluster
 * map on Patterns: a fixed 100x100 viewBox, plain SVG text (no foreignObject),
 * wedge geometry computed from index/count so the same corpus always draws
 * the same picture. Wedge size never encodes anything (there are always 9,
 * evenly split); only fill intensity does, so the shape can't be misread as
 * "this rule matters more" when it's really "this rule got more reports".
 */
function RuleWheel({
  data,
  selected,
  onSelect,
  total,
}: {
  data: RankedRule[];
  selected: string | null;
  onSelect: (name: string) => void;
  total: number;
}) {
  const cx = 50;
  const cy = 50;
  const rOuter = 44;
  const rInner = 24;
  const gap = 2.6;
  const step = 360 / (data.length || 1);
  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <svg viewBox="0 0 100 100" className="h-full w-full" role="img" aria-label="Life-Saving Rules coverage wheel">
      <circle
        cx={cx}
        cy={cy}
        r={(rInner + rOuter) / 2}
        fill="none"
        stroke="var(--color-chart-grid)"
        strokeWidth="0.2"
        strokeDasharray="1 1.4"
      />
      {data.map((d, i) => {
        const a0 = -90 + i * step + gap / 2;
        const a1 = -90 + (i + 1) * step - gap / 2;
        const isSel = selected === d.name;
        const intensity = 0.16 + (d.count / max) * 0.58;
        const rO = isSel ? rOuter + 3 : rOuter;
        return (
          <motion.path
            key={d.name}
            d={wedgePath(cx, cy, rO, rInner, a0, a1)}
            className="cursor-pointer"
            onClick={() => onSelect(d.name)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.045, duration: 0.4 }}
            fill="var(--color-hivis)"
            fillOpacity={isSel ? intensity + 0.26 : intensity}
            stroke={isSel ? 'var(--color-hivis)' : 'var(--color-line-bright)'}
            strokeWidth={isSel ? 0.9 : 0.35}
          >
            <title>{`${d.name} — ${d.count} flagged report${d.count === 1 ? '' : 's'}`}</title>
          </motion.path>
        );
      })}
      <text
        x={cx}
        y={cy - 2}
        textAnchor="middle"
        style={{ fontFamily: 'var(--font-display)', fontSize: 9, fill: 'var(--color-ink)' }}
      >
        {total}
      </text>
      <text
        x={cx}
        y={cy + 6}
        textAnchor="middle"
        style={{ fontFamily: 'var(--font-mono)', fontSize: 2.6, letterSpacing: '0.05em', fill: 'var(--color-ink-4)' }}
      >
        SIF-FLAGGED REPORTS
      </text>
    </svg>
  );
}

export function LifeSavingRulesPage() {
  const [params, setParams] = useSearchParams();
  const { data: ontology, isLoading, error } = useOntology();
  const { data: reports } = useReports({ sif_potential: true, limit: 500 });

  const ranked = useMemo<RankedRule[]>(() => {
    const rules = Object.entries(ontology?.life_saving_rules ?? {});
    const energyEntries = Object.entries(ontology?.energy_types ?? {});
    const barrierEntries = Object.entries(ontology?.barrier_types ?? {});

    const counts = new Map<string, number>();
    (reports?.items ?? []).forEach((r) => {
      if (r.lsr_tag && r.lsr_tag !== 'N/A') counts.set(r.lsr_tag, (counts.get(r.lsr_tag) ?? 0) + 1);
    });

    return rules
      .map(([name, def]) => {
        const energies = energyEntries.filter(([, e]) => e.lsr_tag === name);
        const energyNames = new Set(energies.map(([n]) => n));
        const barriers = barrierEntries.filter(([, b]) => b.controls_energy.some((e) => energyNames.has(e)));
        const failureModes = Array.from(new Set(barriers.flatMap(([, b]) => b.failure_modes)));
        return {
          name,
          icon: def.icon,
          description: def.description,
          count: counts.get(name) ?? 0,
          energies,
          barriers,
          failureModes,
          highEnergyCount: energies.filter(([, e]) => e.is_high_energy).length,
          directBarrierCount: barriers.filter(([, b]) => b.is_direct_control).length,
        };
      })
      .sort((a, b) => b.count - a.count);
  }, [ontology, reports]);

  const totalFlagged = ranked.reduce((s, r) => s + r.count, 0);
  const maxCount = Math.max(...ranked.map((r) => r.count), 1);

  const [selected, setSelected] = useState<string | null>(params.get('rule'));
  useEffect(() => {
    if (!selected && ranked.length) setSelected(ranked[0].name);
  }, [ranked, selected]);

  function choose(name: string) {
    setSelected(name);
    setParams({ rule: name });
  }

  const active = ranked.find((r) => r.name === selected) ?? ranked[0];

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="info" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">REQUIREMENT (B) · RULE TAGGING</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Life-Saving Rules</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          IOGP Report 459. Rule assignment is an <strong className="text-ink-2">ontology lookup</strong> —
          Activity → Energy Type → Life-Saving Rule → Barrier → Failure Mode — from the same taxonomy the
          classification engine uses, not a summary written for this page. Select a rule to trace its full
          chain.
        </p>
      </div>

      {isLoading ? (
        <ScanPanel>
          <PanelLoading rows={6} />
        </ScanPanel>
      ) : error ? (
        <QueryError error={error} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
            <ScanPanel className="lg:col-span-2">
              <PanelHead
                title="9 IOGP RULES"
                sub="Colour intensity = SIF-flagged reports tagged with the rule"
                tone="info"
              />
              <div className="mx-auto aspect-square max-w-[19rem] p-4">
                <RuleWheel data={ranked} selected={active?.name ?? null} onSelect={choose} total={totalFlagged} />
              </div>
            </ScanPanel>

            <ScanPanel className="lg:col-span-3">
              <PanelHead
                title="COVERAGE LEADERBOARD"
                sub="Reports flagged with credible fatal potential, by governing rule"
                tone="hivis"
                right={<Chip tone="neutral">{totalFlagged} FLAGGED</Chip>}
              />
              <div className="max-h-[26rem] divide-y divide-line-faint overflow-y-auto">
                {ranked.map((r, i) => {
                  const Icon = RULE_ICONS[r.icon ?? ''] ?? ShieldOff;
                  const isSel = active?.name === r.name;
                  return (
                    <motion.button
                      key={r.name}
                      type="button"
                      onClick={() => choose(r.name)}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className={cn(
                        'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors',
                        isSel ? 'bg-hivis-wash' : 'hover:bg-surface-2',
                      )}
                    >
                      <span
                        className={cn(
                          'flex h-7 w-7 shrink-0 items-center justify-center rounded-sm border',
                          isSel
                            ? 'border-hivis-edge bg-hivis text-on-hivis'
                            : 'border-line-bright bg-surface-2 text-ink-3',
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" strokeWidth={2.2} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm text-ink">{r.name}</span>
                          <span className="font-mono text-xs tabular text-ink-2">
                            <Counter value={r.count} />
                          </span>
                        </div>
                        <Bar
                          value={r.count / maxCount}
                          tone={isSel ? 'hivis' : 'neutral'}
                          height={3}
                          className="mt-1.5"
                        />
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            </ScanPanel>
          </div>

          {active && (
            <ScanPanel>
              <PanelHead
                title={active.name.toUpperCase()}
                sub={active.description}
                tone="critical"
                right={
                  <Link
                    to={`/reports?lsr=${encodeURIComponent(active.name)}`}
                    className="flex items-center gap-1 font-mono text-2xs tracked text-hivis hover:underline"
                  >
                    VIEW FLAGGED REPORTS
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                }
              />

              {RULE_KNOWLEDGE[active.name] && (
                <div className="border-b border-line bg-surface-2/50 px-4 py-3">
                  <div className="font-mono text-[9px] tracked text-ink-4">WHY THIS RULE EXISTS</div>
                  <p className="mt-1 text-sm leading-relaxed text-ink-2">{RULE_KNOWLEDGE[active.name]}</p>
                </div>
              )}

              {/* The traceability chain, stated as a breadcrumb so the
                  connectivity is legible before you even read the columns. */}
              <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5 font-mono text-2xs tracked text-ink-4">
                <span className="text-hivis">RULE</span>
                <ArrowRight className="h-3 w-3 shrink-0" />
                <span>
                  {active.energies.length} ENERGY TYPE{active.energies.length === 1 ? '' : 'S'}
                </span>
                <ArrowRight className="h-3 w-3 shrink-0" />
                <span>
                  {active.barriers.length} BARRIER{active.barriers.length === 1 ? '' : 'S'}
                </span>
                <ArrowRight className="h-3 w-3 shrink-0" />
                <span>
                  {active.failureModes.length} FAILURE MODE{active.failureModes.length === 1 ? '' : 'S'}
                </span>
                {active.energies.length > 0 && (
                  <span className="ml-auto normal-case tracking-normal text-ink-3">
                    {active.highEnergyCount}/{active.energies.length} high-energy ·{' '}
                    {active.directBarrierCount}/{active.barriers.length || 0} engineered (direct) controls
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 divide-y divide-line-faint lg:grid-cols-3 lg:divide-x lg:divide-y-0">
                <div className="p-4">
                  <Hint content="Every energy type this rule governs, per the EEI energy-wheel taxonomy adapted for upstream oil & gas. The bar is the magnitude class (1-5) used to weight the precursor-density metric.">
                    <div className="mb-2 flex w-fit items-center gap-1.5 font-mono text-[9px] tracked text-ink-4">
                      <Zap className="h-3 w-3" strokeWidth={2.2} />
                      GOVERNS ENERGY TYPES
                    </div>
                  </Hint>
                  <div className="space-y-1.5">
                    {active.energies.map(([name, e]) => (
                      <div key={name} className="rounded-md border border-line bg-surface-2 px-2.5 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs capitalize text-ink">{name}</span>
                          {e.is_high_energy && <Chip tone="critical">HIGH-ENERGY</Chip>}
                        </div>
                        <div className="mt-1.5 flex items-center gap-1">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <span
                              key={i}
                              className={cn(
                                'h-1 flex-1 rounded-full',
                                i < e.magnitude_class ? 'bg-high' : 'bg-surface-3',
                              )}
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                    {active.energies.length === 0 && (
                      <p className="text-xs text-ink-4">No energy type maps to this rule in the taxonomy.</p>
                    )}
                  </div>
                </div>

                <div className="p-4">
                  <Hint content="The barriers that keep each energy type controlled. DIRECT means an engineered/physical barrier effective even under foreseeable human error; the alternative relies on a procedure being followed correctly.">
                    <div className="mb-2 flex w-fit items-center gap-1.5 font-mono text-[9px] tracked text-ink-4">
                      <ShieldCheck className="h-3 w-3" strokeWidth={2.2} />
                      CONTROLLED BY BARRIERS
                    </div>
                  </Hint>
                  <div className="space-y-1.5">
                    {active.barriers.map(([name, b]) => (
                      <div key={name} className="rounded-md border border-line bg-surface-2 px-2.5 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-ink">{name}</span>
                          <Chip tone={b.is_direct_control ? 'low' : 'medium'}>
                            {b.is_direct_control ? 'DIRECT' : 'PROCEDURAL'}
                          </Chip>
                        </div>
                        <div className="mt-1 font-mono text-2xs text-ink-4">
                          {b.control_level.toUpperCase()} CONTROL
                        </div>
                      </div>
                    ))}
                    {active.barriers.length === 0 && (
                      <p className="text-xs text-ink-4">
                        No barrier in the taxonomy controls this rule&rsquo;s energy types.
                      </p>
                    )}
                  </div>
                </div>

                <div className="p-4">
                  <Hint content="How the barriers above are catalogued to typically fail — the fixed vocabulary the classification engine tags a report's barrier_status against.">
                    <div className="mb-2 flex w-fit items-center gap-1.5 font-mono text-[9px] tracked text-ink-4">
                      <TriangleAlert className="h-3 w-3" strokeWidth={2.2} />
                      HOW THOSE BARRIERS TYPICALLY FAIL
                    </div>
                  </Hint>
                  <div className="flex flex-wrap gap-1.5">
                    {active.failureModes.map((f) => (
                      <Chip key={f} tone="high">
                        {f}
                      </Chip>
                    ))}
                    {active.failureModes.length === 0 && (
                      <p className="text-xs text-ink-4">No failure modes catalogued.</p>
                    )}
                  </div>
                </div>
              </div>
            </ScanPanel>
          )}
        </>
      )}
    </div>
  );
}
