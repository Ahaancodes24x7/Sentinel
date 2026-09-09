import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Activity, ArrowRight, Boxes, GitBranch, Radar, ShieldOff, Zap } from 'lucide-react';
import { Counter, PulseDot } from '../components/kinetic';

const PILLARS = [
  {
    icon: Zap,
    title: 'Energy, not outcome',
    body: 'A dropped wrench that lands 30 cm from a boot is a "no injury" event and a live high-energy precursor. The classifier is built on what was present, not on what happened.',
  },
  {
    icon: ShieldOff,
    title: 'Barrier state as the signal',
    body: 'A site with 50 reports that all show a confirmed barrier is safer than one with 10 where six show none. Density is computed from barrier gaps, not report volume.',
  },
  {
    icon: Boxes,
    title: 'Rules by lookup, not guesswork',
    body: 'Life-Saving Rule assignment is an ontology lookup from the extracted energy type — small, fixed, auditable, and it never needs retraining.',
  },
  {
    icon: GitBranch,
    title: 'Patterns over structure',
    body: 'Clustering runs on the extracted event frame, so differently-worded reports about the same barrier failure land together instead of scattering across vocabulary.',
  },
];

const CHAIN = ['ACTIVITY', 'ENERGY', 'BARRIER', 'EXPOSURE', 'CONSEQUENCE', 'LSR'];

export function LandingPage() {
  return (
    <div className="field-grid scanlines relative min-h-screen overflow-x-hidden bg-bg">
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="drift absolute -top-40 left-1/3 h-[40rem] w-[40rem] rounded-full bg-hivis/[0.055] blur-[130px]" />
        <div
          className="drift absolute bottom-0 right-0 h-[32rem] w-[32rem] rounded-full bg-critical/[0.04] blur-[130px]"
          style={{ animationDelay: '-10s' }}
        />
      </div>

      {/* Nav */}
      <header className="relative z-10 flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-hivis">
            <Activity className="h-4 w-4 text-on-hivis" strokeWidth={2.75} />
          </div>
          <div>
            <div className="font-display text-lg leading-none text-ink">SENTINEL</div>
            <div className="font-mono text-[9px] tracked text-ink-4">PS 26165</div>
          </div>
        </div>
        <Link
          to="/login"
          className="flex items-center gap-2 rounded-md bg-hivis px-3.5 py-2 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.03]"
        >
          OPEN CONSOLE <ArrowRight className="h-3 w-3" strokeWidth={2.6} />
        </Link>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-16 pt-14">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="flex items-center gap-2">
            <PulseDot tone="critical" size={7} />
            <span className="font-mono text-2xs tracked text-ink-3">
              AI/NLP ENGINE FOR SIF-PRECURSOR DETECTION · OIL INDIA LIMITED
            </span>
          </div>

          <h1 className="mt-6 font-display text-6xl leading-[0.92] text-ink sm:text-[5.5rem]">
            Nobody was hurt.
            <br />
            <span className="text-hivis">Somebody nearly died.</span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-2">
            Actual outcome severity is a bad predictor of fatal potential. Sentinel reads free-text
            HSSE observations and infers whether the situation carried credible fatal potential —
            then explains that inference in the terms an HSE engineer already uses.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/login"
              className="flex items-center gap-2 rounded-md bg-hivis px-5 py-3 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.02]"
            >
              ENTER CONSOLE <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
            </Link>
            <a
              href="https://www.iogp.org/bookstore/product/iogp-report-459-life-saving-rules/"
              target="_blank"
              rel="noreferrer noopener"
              className="rounded-md border border-line-bright px-5 py-3 font-mono text-2xs tracked text-ink-2 transition-colors hover:border-hivis-edge hover:text-hivis"
            >
              IOGP REPORT 459
            </a>
          </div>
        </motion.div>

        {/* Reasoning chain */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.6 }}
          className="mt-16 rounded-lg border border-line bg-surface/70 p-6 backdrop-blur-xl"
        >
          <div className="font-mono text-2xs tracked text-ink-4">
            THE REASONING CHAIN, EXTRACTED AUTOMATICALLY
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {CHAIN.map((step, i) => (
              <motion.div
                key={step}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 + i * 0.08 }}
                className="flex items-center gap-2"
              >
                <span className="rounded-sm border border-hivis-edge bg-hivis-wash px-2.5 py-1.5 font-mono text-2xs tracked text-hivis">
                  {step}
                </span>
                {i < CHAIN.length - 1 && <ArrowRight className="h-3 w-3 text-ink-4" />}
              </motion.div>
            ))}
          </div>
          <p className="mt-4 max-w-3xl text-sm text-ink-3">
            Learned extraction feeds a small, fixed decision structure adapted from the EEI Safety
            Classification &amp; Learning model. The reasoning step is inspectable line by line and
            never needs retraining; only the extraction is statistical, and it fails into a
            human-review bucket rather than guessing.
          </p>
        </motion.div>

        {/* Corpus stats */}
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'SYNTHETIC REPORTS', value: 25000 },
            { label: 'GOLD NER SPANS', value: 118443 },
            { label: 'ENERGY TYPES', value: 14 },
            { label: 'LIFE-SAVING RULES', value: 9 },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + i * 0.08 }}
              className="rounded-panel border border-line bg-surface/60 p-4 backdrop-blur"
            >
              <div className="font-display text-3xl text-hivis">
                <Counter value={stat.value} duration={1.6} />
              </div>
              <div className="mt-1 font-mono text-[9px] tracked text-ink-4">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pillars */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-20">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {PILLARS.map((pillar, i) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ delay: i * 0.08, duration: 0.5 }}
              className="group rounded-panel border border-line bg-surface/60 p-6 backdrop-blur transition-colors hover:border-hivis-edge"
            >
              <pillar.icon
                className="h-5 w-5 text-hivis transition-transform group-hover:scale-110"
                strokeWidth={1.9}
              />
              <h3 className="mt-3 font-display text-2xl text-ink">{pillar.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-3">{pillar.body}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-6 rounded-panel border border-medium-edge bg-medium-wash px-5 py-4">
          <div className="flex items-center gap-2">
            <Radar className="h-4 w-4 text-medium" strokeWidth={2} />
            <span className="font-mono text-2xs tracked text-medium">SCOPE &amp; HONESTY</span>
          </div>
          <p className="mt-2 text-sm text-ink-2">
            This prototype runs on a clearly-labelled synthetic corpus. It is not connected to OIL
            systems, it does not predict fatalities, and its metrics are internal consistency
            validation rather than production validation. Everything it does claim, it shows the
            evidence for.
          </p>
        </div>
      </section>

      <footer className="relative z-10 border-t border-line px-6 py-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <span className="font-mono text-2xs text-ink-4">
            SENTINEL · SIH 2026 · PS 26165 · SMART AUTOMATION
          </span>
          <Link to="/login" className="font-mono text-2xs tracked text-hivis hover:underline">
            OPEN CONSOLE →
          </Link>
        </div>
      </footer>
    </div>
  );
}
