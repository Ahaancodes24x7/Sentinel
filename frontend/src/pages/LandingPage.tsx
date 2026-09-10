import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowUpRight, Boxes, GitBranch, ShieldOff, Zap } from 'lucide-react';
import { Chip, PulseDot } from '../components/kinetic';
import { SentinelLogo } from '../components/common/SentinelMark';

/* --------------------------------------------------------------------------
 * Institutional pass, not a startup landing page.
 *
 * The brief this follows: real operational hierarchy over marketing copy,
 * numbers presented as information rather than bragging cards, capabilities
 * introduced after the hero rather than crammed into it, and neon reserved
 * for "active / detected / action" rather than used as the page's whole
 * personality. See DESIGN.md for the fuller rationale if it's added there.
 * ----------------------------------------------------------------------- */

const NAV_LINKS = [
  { href: '#platform', label: 'Platform' },
  { href: '#intelligence', label: 'Safety Intelligence' },
  { href: '#sites', label: 'Sites' },
  { href: '#about', label: 'About' },
];

const PROCESS = [
  {
    n: '01',
    title: 'Extract',
    body: 'Activity, energy source, barrier state, exposure and consequence are pulled from the free-text report.',
  },
  {
    n: '02',
    title: 'Reason',
    body: 'A fixed, auditable decision structure — not a model — maps the extracted frame to SIF potential and Life-Saving Rule.',
  },
  {
    n: '03',
    title: 'Discover',
    body: 'Clustering runs on the extracted frame, so recurring barrier failures surface across sites and wording.',
  },
  {
    n: '04',
    title: 'Act',
    body: 'High-confidence SIF precursors route to review; everything else keeps its evidence attached for audit.',
  },
];

const CAPABILITIES = [
  {
    n: '01',
    icon: Zap,
    title: 'Energy, not outcome',
    body: 'A dropped wrench that lands 30 cm from a boot is a "no injury" event and a live high-energy precursor. The classifier is built on what was present, not on what happened.',
  },
  {
    n: '02',
    icon: ShieldOff,
    title: 'Barrier state as the signal',
    body: 'A site with 50 reports that all show a confirmed barrier is safer than one with 10 where six show none. Density is computed from barrier gaps, not report volume.',
  },
  {
    n: '03',
    icon: Boxes,
    title: 'Rules by lookup, not guesswork',
    body: 'Life-Saving Rule assignment is an ontology lookup from the extracted energy type — small, fixed, auditable, and it never needs retraining.',
  },
  {
    n: '04',
    icon: GitBranch,
    title: 'Patterns over structure',
    body: 'Clustering runs on the extracted event frame, so differently-worded reports about the same barrier failure land together instead of scattering across vocabulary.',
  },
];

const SITES = [
  { name: 'Duliajan', role: 'Field headquarters & processing' },
  { name: 'Digboi', role: 'Refinery operations' },
  { name: 'Moran', role: 'Production field' },
];

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const } },
};

export function LandingPage() {
  return (
    <div className="field-grid scanlines relative min-h-screen overflow-x-hidden bg-bg">
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="drift absolute -top-40 left-1/3 h-[40rem] w-[40rem] rounded-full bg-hivis/[0.035] blur-[150px]" />
      </div>

      {/* Nav */}
      <header className="relative z-10 border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <SentinelLogo caption="OIL INDIA LIMITED" size={26} />

          <nav className="hidden items-center gap-7 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="font-mono text-2xs tracked text-ink-3 transition-colors hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <Link
            to="/login"
            className="flex items-center gap-2 rounded-md bg-hivis px-3.5 py-2 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.03]"
          >
            OPEN CONSOLE <ArrowRight className="h-3 w-3" strokeWidth={2.6} />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section id="platform" className="relative z-10 mx-auto max-w-6xl px-6 pb-20 pt-16">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.3fr_0.7fr] lg:gap-10">
          <motion.div initial="hidden" animate="show" variants={fadeUp}>
            <div className="flex items-center gap-2">
              <PulseDot tone="hivis" size={6} />
              <span className="font-mono text-2xs tracked text-ink-3">
                SAFETY INTELLIGENCE PLATFORM &middot; OIL INDIA LIMITED
              </span>
            </div>

            <h1 className="mt-5 font-display text-4xl leading-[1.12] text-ink sm:text-5xl lg:text-[3.25rem]">
              Detect the precursor
              <br />
              before it becomes the incident.
            </h1>

            <p className="mt-6 max-w-lg text-base leading-relaxed text-ink-2">
              Sentinel reads unsafe-act, unsafe-condition and near-miss reports and infers SIF
              potential, barrier failure and Life-Saving Rule exposure — in the terms an HSE
              engineer already uses.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                to="/login"
                className="flex items-center gap-2 rounded-md bg-hivis px-5 py-3 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.02]"
              >
                OPEN SAFETY CONSOLE <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
              </Link>
              <a
                href="https://www.iogp.org/bookstore/product/iogp-report-459-life-saving-rules/"
                target="_blank"
                rel="noreferrer noopener"
                className="flex items-center gap-1.5 rounded-md border border-line-bright px-5 py-3 font-mono text-2xs tracked text-ink-2 transition-colors hover:border-hivis-edge hover:text-hivis"
              >
                IOGP REPORT 459 <ArrowUpRight className="h-3 w-3" strokeWidth={2.4} />
              </a>
            </div>

            <div className="mt-10 flex items-center gap-6 border-t border-line pt-5">
              {[
                ['9', 'Life-Saving Rules'],
                ['14', 'Energy types'],
                ['3', 'OIL sites modelled'],
              ].map(([value, label]) => (
                <div key={label}>
                  <div className="font-display text-xl text-ink">{value}</div>
                  <div className="mt-0.5 font-mono text-[9px] tracked text-ink-4">{label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          >
            <HeroPanel />
          </motion.div>
        </div>
      </section>

      {/* Process strip */}
      <section className="relative z-10 border-y border-line bg-surface/40">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="font-mono text-2xs tracked text-ink-4">FROM REPORT TO SAFETY INTELLIGENCE</div>
          <div className="mt-6 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-0">
            {PROCESS.map((step, i) => (
              <motion.div
                key={step.n}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.45 }}
                className="lg:border-l lg:border-line lg:pl-6 lg:[&:first-child]:border-l-0 lg:[&:first-child]:pl-0"
              >
                <div className="font-mono text-2xs tracked text-hivis">{step.n}</div>
                <div className="mt-2 font-display text-lg text-ink">{step.title}</div>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-3">{step.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Product preview: report -> reasoning */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-16">
        <div className="max-w-2xl">
          <div className="font-mono text-2xs tracked text-ink-4">HOW A REPORT IS READ</div>
          <h2 className="mt-3 font-display text-3xl text-ink">
            The reasoning is inspectable, not a black box.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-3">
            Extraction is the only statistical step. It feeds a small, fixed decision structure —
            adapted from the EEI Safety Classification &amp; Learning model — that can be read line
            by line and never needs retraining.
          </p>
        </div>

        <ReasoningMock />
      </section>

      {/* Capabilities */}
      <section id="intelligence" className="relative z-10 border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="font-mono text-2xs tracked text-ink-4">SAFETY INTELLIGENCE</div>
          <h2 className="mt-3 max-w-xl font-display text-3xl text-ink">
            Built on what the report contains, not on what happened.
          </h2>

          <div className="mt-10 grid grid-cols-1 gap-x-10 gap-y-10 md:grid-cols-2">
            {CAPABILITIES.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.5 }}
                className="flex gap-4 border-t border-line pt-5"
              >
                <span className="font-mono text-2xs tracked text-ink-4">{c.n}</span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <c.icon className="h-4 w-4 text-hivis" strokeWidth={1.9} />
                    <h3 className="font-display text-lg text-ink">{c.title}</h3>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-ink-3">{c.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Sites */}
      <section id="sites" className="relative z-10 border-t border-line bg-surface/40">
        <div className="mx-auto max-w-6xl px-6 py-14">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="font-mono text-2xs tracked text-ink-4">OPERATIONAL VIEW</div>
              <h2 className="mt-2 font-display text-2xl text-ink">Demonstration sites</h2>
            </div>
            <Link
              to="/login"
              className="flex items-center gap-1.5 font-mono text-2xs tracked text-hivis hover:underline"
            >
              VIEW SITE RISK <ArrowRight className="h-3 w-3" strokeWidth={2.4} />
            </Link>
          </div>

          <div className="mt-8 divide-y divide-line border-y border-line">
            {SITES.map((site) => (
              <div key={site.name} className="flex items-center justify-between gap-4 py-4">
                <div className="flex items-center gap-3">
                  <PulseDot tone="hivis" size={6} />
                  <span className="font-display text-lg text-ink">{site.name}</span>
                </div>
                <span className="font-mono text-2xs tracked text-ink-4">{site.role}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Prototype status */}
      <section id="about" className="relative z-10 mx-auto max-w-6xl px-6 py-14">
        <div className="rounded-panel border border-line px-5 py-4">
          <div className="font-mono text-2xs tracked text-ink-4">PROTOTYPE &amp; VALIDATION DATA</div>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-3">
            This demonstration runs on a labelled synthetic corpus — 25,000 safety observations
            across 14 energy types, annotated for 9 Life-Saving Rules. Sentinel is not connected to
            OIL production systems or live incident data, and its metrics are internal-consistency
            validation rather than production validation. Everything it claims, it shows the
            evidence for.
          </p>
        </div>
      </section>

      <footer className="relative z-10 border-t border-line px-6 py-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <span className="font-mono text-2xs text-ink-4">
            SENTINEL &middot; SIH 2026 &middot; PS 26165 &middot; SMART AUTOMATION
          </span>
          <Link to="/login" className="font-mono text-2xs tracked text-hivis hover:underline">
            OPEN CONSOLE →
          </Link>
        </div>
      </footer>
    </div>
  );
}

/* ==========================================================================
 * Hero visual: a constructed industrial skyline with a detection overlay,
 * standing in for photography we don't have licensed. It's built from the
 * product's own vocabulary (barrier / exposure / demo feed) rather than
 * generic decoration, so it reads as "this is what the system watches" and
 * not as an abstract glow.
 * ========================================================================== */
function HeroPanel() {
  return (
    <div className="overflow-hidden rounded-panel border border-line bg-surface shadow-panel">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-2">DULIAJAN &middot; CAM DUL-01</span>
        </div>
        <span className="font-mono text-[9px] tracked text-ink-4">DEMO FEED</span>
      </div>

      <div className="relative aspect-[4/3] w-full">
        <svg viewBox="0 0 480 360" className="h-full w-full" preserveAspectRatio="xMidYMax slice">
          <defs>
            <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-void)" />
              <stop offset="100%" stopColor="var(--color-bg)" />
            </linearGradient>
            <radialGradient id="rim" cx="50%" cy="100%" r="70%">
              <stop offset="0%" stopColor="var(--color-hivis)" stopOpacity="0.10" />
              <stop offset="100%" stopColor="var(--color-hivis)" stopOpacity="0" />
            </radialGradient>
          </defs>

          <rect width="480" height="360" fill="url(#sky)" />
          <rect y="235" width="480" height="125" fill="url(#rim)" />

          {/* Flare stack */}
          <line x1="120" y1="240" x2="120" y2="70" stroke="var(--color-ink-4)" strokeWidth="2" />
          <polygon points="120,70 112,88 128,88" fill="var(--color-high)" opacity="0.85" />

          {/* Pipe rack */}
          <line x1="150" y1="232" x2="300" y2="232" stroke="var(--color-ink-4)" strokeWidth="2" />
          {Array.from({ length: 8 }).map((_, i) => (
            <line
              key={i}
              x1={158 + i * 19}
              y1="232"
              x2={158 + i * 19}
              y2="246"
              stroke="var(--color-ink-4)"
              strokeWidth="2"
            />
          ))}

          {/* Storage tanks */}
          {[
            { x: 320, w: 46, h: 70 },
            { x: 372, w: 36, h: 54 },
          ].map((t) => (
            <g key={t.x}>
              <rect
                x={t.x}
                y={240 - t.h}
                width={t.w}
                height={t.h}
                fill="var(--color-surface-3)"
                stroke="var(--color-line-bright)"
              />
              <ellipse cx={t.x + t.w / 2} cy={240 - t.h} rx={t.w / 2} ry="5" fill="var(--color-surface-hi)" />
            </g>
          ))}

          {/* Derrick */}
          <line x1="60" y1="240" x2="90" y2="60" stroke="var(--color-ink-4)" strokeWidth="2" />
          <line x1="110" y1="240" x2="90" y2="60" stroke="var(--color-ink-4)" strokeWidth="2" />
          <line x1="70" y1="170" x2="102" y2="170" stroke="var(--color-ink-4)" strokeWidth="1.5" />
          <line x1="75" y1="120" x2="97" y2="120" stroke="var(--color-ink-4)" strokeWidth="1.5" />

          {/* Ground */}
          <line x1="0" y1="240" x2="480" y2="240" stroke="var(--color-line-bright)" strokeWidth="1.5" />

          {/* Detection overlay on the pipe rack / tank cluster */}
          <rect
            x="146"
            y="160"
            width="270"
            height="84"
            fill="none"
            stroke="var(--color-hivis)"
            strokeWidth="1.5"
            strokeDasharray="5 4"
            rx="3"
          />
          {[
            [146, 160],
            [416, 160],
            [146, 244],
            [416, 244],
          ].map(([x, y], i) => (
            <path
              key={i}
              d={`M${x + (x === 146 ? 0 : -10)} ${y} h10 M${x} ${y + (y === 160 ? 0 : -10)} v10`}
              stroke="var(--color-hivis)"
              strokeWidth="2"
              strokeLinecap="round"
            />
          ))}
        </svg>

        <div className="absolute left-4 top-4">
          <Chip tone="hivis" dot>
            BARRIER: CONFIRMED
          </Chip>
        </div>
        <div className="absolute bottom-4 left-4">
          <Chip tone="neutral">EXPOSURE: NONE</Chip>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================================
 * Report -> reasoning mock. Two panes: the free-text input on the left, the
 * extracted frame and rule mapping on the right. Static content — this is a
 * representative example, not a live call.
 * ========================================================================== */
function ReasoningMock() {
  const fields: Array<[string, string, 'hivis' | 'high' | 'critical' | 'neutral']> = [
    ['ENERGY', 'Stored pressure — isolated line', 'high'],
    ['BARRIER', 'LOTO not confirmed at time of report', 'critical'],
    ['EXPOSURE', 'Direct — technician within 1 m', 'high'],
    ['CONSEQUENCE', 'Credible fatal potential', 'critical'],
    ['LSR', 'Life-Saving Rule 3 — Line of Fire', 'hivis'],
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mt-8 grid grid-cols-1 overflow-hidden rounded-panel border border-line lg:grid-cols-2"
    >
      <div className="border-b border-line p-5 lg:border-b-0 lg:border-r">
        <div className="font-mono text-2xs tracked text-ink-4">REPORT · UNSTRUCTURED TEXT</div>
        <p className="mt-3 text-sm leading-relaxed text-ink-2">
          "Found isolation valve on the 4-inch line still showing line pressure during scheduled
          maintenance. Technician had already begun disconnecting the flange when the reading was
          noticed. Work stopped, no injury."
        </p>
        <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-line-faint pt-4 font-mono text-2xs tracked text-ink-4">
          <span>SITE: DULIAJAN</span>
          <span>TYPE: NEAR MISS</span>
          <span>OUTCOME: NO INJURY</span>
        </div>
      </div>
      <div className="p-5">
        <div className="font-mono text-2xs tracked text-ink-4">EXTRACTED &amp; REASONED</div>
        <div className="mt-3 space-y-3">
          {fields.map(([label, value, tone]) => (
            <div key={label} className="flex items-start justify-between gap-4">
              <span className="w-24 shrink-0 font-mono text-2xs tracked text-ink-4">{label}</span>
              <span
                className={
                  tone === 'critical'
                    ? 'text-right text-sm text-critical'
                    : tone === 'high'
                      ? 'text-right text-sm text-high'
                      : tone === 'hivis'
                        ? 'text-right text-sm text-hivis'
                        : 'text-right text-sm text-ink-2'
                }
              >
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
