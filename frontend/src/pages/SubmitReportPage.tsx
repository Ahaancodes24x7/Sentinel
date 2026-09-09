import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, LoaderCircle, PenLine, RotateCcw, Send } from 'lucide-react';
import { Bar, Chip, PanelHead, PulseDot, ScanPanel, type Tone } from '../components/kinetic';
import { Hint, HINTS } from '../components/common/Hint';
import { QueryError } from '../components/common/QueryState';
import { api, ApiError } from '../api/client';
import { useOntology } from '../api/hooks';
import { BUCKET_META, type Bucket, type ReportDetail } from '../api/types';
import { cn } from '../lib/cn';

const BUCKET_HINT: Record<Bucket, string> = {
  HIGH_CONF_SIF: HINTS.bucketPriority,
  LOW_CONF_REVIEW: HINTS.bucketReview,
  NEEDS_MORE_INFO: HINTS.bucketIncomplete,
  HIGH_CONF_NON_SIF: HINTS.bucketCleared,
};

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

const SPAN_STYLE: Record<string, string> = {
  activity: 'bg-info-wash text-info',
  hazard: 'bg-critical-wash text-critical',
  energy_type: 'bg-critical-wash text-critical',
  barrier: 'bg-medium-wash text-medium',
  barrier_status: 'bg-medium-wash text-medium',
  exposure: 'bg-high-wash text-high',
  location: 'bg-violet-wash text-violet',
};

/** Worked examples, so a first-time user can see what a useful report looks like. */
const EXAMPLES = [
  {
    label: 'Near-miss, nobody hurt',
    site: 'Rig 7',
    text:
      'Went to change the pressure gauge on the separator this morning. The line was still live, nobody had put a lock on the valve, and I was stood right in front of the fitting when I cracked it. Got lucky, no injury.',
  },
  {
    label: 'Unsafe condition, no incident',
    site: 'Rig 4',
    text:
      'Crane was lifting a skid across the pipe rack. No barricade had been set up underneath and two fitters were working directly below the load. Job stopped and the area cleared.',
  },
  {
    label: 'Minor injury, low hazard',
    site: 'Workshop Central',
    text:
      'Housekeeping in the workshop was poor, offcuts left across the walkway. A fitter tripped and grazed his hand. First aid dressing applied at the clinic.',
  },
];

export function SubmitReportPage() {
  const { data: ontology } = useOntology();
  const sites = ontology?.sites?.map((s) => s.name) ?? [];

  const [site, setSite] = useState('');
  const [text, setText] = useState('');
  const [role, setRole] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  const tooShort = text.trim().length < 15;
  const canSubmit = Boolean(site) && !tooShort && !busy;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.post<ReportDetail>('/reports/submit', {
        site,
        report_text: text.trim(),
        reporter_role: role || null,
      });
      setResult(res);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
    setText('');
    setRole('');
  }

  function loadExample(ex: (typeof EXAMPLES)[number]) {
    setSite(ex.site);
    setText(ex.text);
    setResult(null);
    setError(null);
  }

  const cls = result?.classification;
  const spans = result?.extracted_fields?.evidence_spans ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">FIELD OBSERVATION</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">File a Report</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-ink-3">
          Describe what you saw in plain words. You do not need to know whether it was serious —
          working that out is the system&rsquo;s job, and it will show you its reasoning straight
          away.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
        {/* ---------------- Form ---------------- */}
        <ScanPanel className="lg:col-span-3">
          <PanelHead title="NEW OBSERVATION" sub="Analysed the moment you submit" />
          <form onSubmit={submit} className="space-y-3 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="font-mono text-[9px] tracked text-ink-4">SITE *</span>
                <select
                  value={site}
                  onChange={(e) => setSite(e.target.value)}
                  required
                  className="mt-1 w-full rounded-md border border-line bg-surface-2 px-2.5 py-2 text-sm text-ink focus:border-hivis-edge focus:outline-none"
                >
                  <option value="">Select a site…</option>
                  {sites.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="font-mono text-[9px] tracked text-ink-4">YOUR ROLE</span>
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. fitter, rigger, supervisor"
                  className="mt-1 w-full rounded-md border border-line bg-surface-2 px-2.5 py-2 text-sm text-ink placeholder:text-ink-4 focus:border-hivis-edge focus:outline-none"
                />
              </label>
            </div>

            <label className="block">
              <span className="flex items-center gap-1.5 font-mono text-[9px] tracked text-ink-4">
                WHAT DID YOU SEE? *
                <Hint
                  side="right"
                  content="Say what was going on, what could have hurt someone, whether any control was in place, and who was nearby. Plain words are fine — the engine handles abbreviations, typos and Hindi phrasing."
                >
                  <span className="cursor-help underline decoration-dotted">writing tips</span>
                </Hint>
              </span>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={7}
                required
                placeholder="Crane was lifting a skid across the pipe rack. No barricade underneath and two fitters were working directly below the load…"
                className="mt-1 w-full resize-y rounded-md border border-line bg-surface-2 px-3 py-2 text-sm leading-relaxed text-ink placeholder:text-ink-4 focus:border-hivis-edge focus:outline-none"
              />
              <span
                className={cn(
                  'mt-1 block font-mono text-2xs',
                  tooShort && text.length > 0 ? 'text-high' : 'text-ink-4',
                )}
              >
                {text.trim().length} characters
                {tooShort && text.length > 0 && ' — a little more detail, please'}
              </span>
            </label>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="submit"
                disabled={!canSubmit}
                className={cn(
                  'flex items-center gap-2 rounded-md px-4 py-2.5 font-mono text-2xs tracked transition-transform',
                  canSubmit
                    ? 'bg-hivis text-on-hivis hover:scale-[1.02]'
                    : 'cursor-not-allowed bg-surface-3 text-ink-4',
                )}
              >
                {busy ? (
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Send className="h-3.5 w-3.5" strokeWidth={2.4} />
                )}
                {busy ? 'ANALYSING' : 'SUBMIT & ANALYSE'}
              </button>

              {Boolean(result || error) && (
                <button
                  type="button"
                  onClick={reset}
                  className="flex items-center gap-1.5 rounded-md border border-line-bright px-3 py-2.5 font-mono text-2xs tracked text-ink-2 hover:border-hivis-edge hover:text-hivis"
                >
                  <RotateCcw className="h-3 w-3" /> NEW REPORT
                </button>
              )}
            </div>
          </form>

          {/* Examples */}
          <div className="border-t border-line px-4 py-3">
            <div className="font-mono text-[9px] tracked text-ink-4">
              OR TRY A WORKED EXAMPLE
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  type="button"
                  onClick={() => loadExample(ex)}
                  className="rounded-sm border border-line-bright bg-surface-2 px-2 py-1 font-mono text-2xs text-ink-2 transition-colors hover:border-hivis-edge hover:text-hivis"
                >
                  <PenLine className="mr-1 inline h-2.5 w-2.5" />
                  {ex.label}
                </button>
              ))}
            </div>
          </div>
        </ScanPanel>

        {/* ---------------- Result ---------------- */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {error ? (
              <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <QueryError
                  error={
                    error instanceof ApiError
                      ? error
                      : new ApiError('Could not analyse this report')
                  }
                />
              </motion.div>
            ) : busy ? (
              <motion.div key="busy" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <ScanPanel className="p-6 text-center">
                  <PulseDot tone="hivis" size={8} className="mx-auto" />
                  <div className="mt-3 font-mono text-2xs tracked text-ink-3">
                    RUNNING STAGE 0–3
                  </div>
                  <p className="mt-1 text-xs text-ink-4">
                    Extracting energy, barrier and exposure, then applying the SCL decision logic.
                  </p>
                </ScanPanel>
              </motion.div>
            ) : result && cls ? (
              <motion.div
                key="res"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-3"
              >
                {/* Verdict */}
                <div
                  className={cn(
                    'rounded-panel border p-4',
                    cls.sif_potential
                      ? 'border-critical-edge bg-critical-wash'
                      : 'border-low-edge bg-low-wash',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <PulseDot tone={cls.sif_potential ? 'critical' : 'low'} size={7} />
                    <Hint content={HINTS.precursor} side="left">
                      <span className="cursor-help font-mono text-2xs tracked text-ink-2">
                        {cls.sif_potential ? 'SIF PRECURSOR' : 'NO PRECURSOR FOUND'}
                      </span>
                    </Hint>
                  </div>

                  <p className="mt-2 text-sm leading-relaxed text-ink">
                    {cls.sif_potential
                      ? 'This describes a situation that could credibly have killed someone. It has been sent for review.'
                      : 'On the evidence in this report, no credible fatal potential was found. It has been logged.'}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    <Hint content={BUCKET_HINT[cls.bucket]}>
                      <Chip tone={BUCKET_TONE[cls.bucket]} dot>
                        {BUCKET_META[cls.bucket]?.short}
                      </Chip>
                    </Hint>
                    {cls.lsr_tag && cls.lsr_tag !== 'N/A' && (
                      <Hint content={HINTS.lsr}>
                        <Chip tone="hivis">{cls.lsr_tag}</Chip>
                      </Hint>
                    )}
                  </div>

                  <div className="mt-3">
                    <div className="flex justify-between font-mono text-2xs text-ink-4">
                      <Hint content={HINTS.evidenceStrength}>
                        <span className="cursor-help">EVIDENCE STRENGTH</span>
                      </Hint>
                      <span className="tabular text-ink-2">
                        {(cls.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <Bar
                      value={cls.confidence}
                      tone={cls.sif_potential ? 'critical' : 'low'}
                      className="mt-1"
                    />
                  </div>
                </div>

                {/* Why */}
                <ScanPanel>
                  <PanelHead title="WHY" sub="Built from the words in your report" tone="hivis" />
                  <div className="p-4">
                    <p className="text-sm leading-relaxed text-ink-2">{cls.justification}</p>

                    {spans.length > 0 && (
                      <div className="mt-3">
                        <div className="font-mono text-[9px] tracked text-ink-4">
                          WHAT IT PICKED UP
                        </div>
                        <div className="mt-1.5 space-y-1">
                          {spans.map((s, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <span
                                className={cn(
                                  'shrink-0 rounded-sm px-1 py-0.5 font-mono text-[9px] tracked',
                                  SPAN_STYLE[s.field] ?? 'bg-surface-3 text-ink-2',
                                )}
                              >
                                {s.field.replace(/_/g, ' ').toUpperCase()}
                              </span>
                              <span className="text-xs text-ink-2">&ldquo;{s.text}&rdquo;</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="border-t border-line px-4 py-2.5">
                    <Link
                      to={`/reports/${result.report_id}`}
                      className="flex items-center gap-1.5 font-mono text-2xs tracked text-hivis hover:underline"
                    >
                      SEE FULL BREAKDOWN <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </ScanPanel>
              </motion.div>
            ) : (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <ScanPanel className="p-6" active={false}>
                  <div className="font-mono text-2xs tracked text-ink-4">WHAT HAPPENS NEXT</div>
                  <ol className="mt-3 space-y-3">
                    {[
                      ['Your words are cleaned up', 'Abbreviations expanded, typos and mixed-language phrasing handled.'],
                      ['The situation is extracted', 'What was being done, what could hurt someone, whether a control was in place, who was nearby.'],
                      ['A fixed safety logic is applied', 'The same energy–barrier–exposure test an HSE engineer uses. No black box.'],
                      ['It is routed', 'Serious ones go to the top of the review queue. Unclear ones go to a person, not a guess.'],
                    ].map(([title, body], i) => (
                      <li key={title} className="flex gap-2.5">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-line-bright bg-surface-2 font-mono text-[9px] text-hivis">
                          {i + 1}
                        </span>
                        <div>
                          <div className="text-sm text-ink">{title}</div>
                          <div className="text-xs text-ink-3">{body}</div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </ScanPanel>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
