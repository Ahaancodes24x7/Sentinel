/**
 * Hover/focus explanations.
 *
 * This console is full of domain vocabulary — "precursor", "barrier gap",
 * "CUSUM", "direct control" — that is obvious to an HSE engineer and opaque to
 * everyone else. Rather than cluttering the screen with permanent captions,
 * every non-obvious control carries a hint you can hover.
 *
 * Two rules kept it from becoming noise:
 *   - Hints explain WHAT A CONTROL DOES or WHAT A TERM MEANS. They never repeat
 *     the label they are attached to.
 *   - They open on focus as well as hover, so they are reachable by keyboard
 *     and not just by mouse.
 */

import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { HelpCircle } from 'lucide-react';
import { cn } from '../../lib/cn';

type Side = 'top' | 'bottom' | 'left' | 'right';

interface HintProps {
  /** The explanation. Keep it to one or two short sentences. */
  content: React.ReactNode;
  children: React.ReactElement | React.ReactNode;
  side?: Side;
  /** Delay before opening, ms. Stops hints flashing as the cursor crosses the UI. */
  delay?: number;
  className?: string;
  maxWidth?: number;
}

export function Hint({
  content,
  children,
  side = 'top',
  delay = 350,
  className,
  maxWidth = 260,
}: HintProps) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const anchorRef = useRef<HTMLSpanElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const id = useId();

  function show() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(true), delay);
  }
  function hide() {
    if (timer.current) clearTimeout(timer.current);
    setOpen(false);
  }

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  // Close on Escape — a hint should never trap the reader.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Position after paint, then clamp into the viewport. Rendered through a
  // portal so a hint never gets clipped by a panel's overflow:hidden.
  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return;
    const a = anchorRef.current.getBoundingClientRect();
    const b = bubbleRef.current?.getBoundingClientRect();
    const w = b?.width ?? maxWidth;
    const h = b?.height ?? 44;
    const gap = 8;

    let top: number;
    let left: number;
    switch (side) {
      case 'bottom':
        top = a.bottom + gap;
        left = a.left + a.width / 2 - w / 2;
        break;
      case 'left':
        top = a.top + a.height / 2 - h / 2;
        left = a.left - w - gap;
        break;
      case 'right':
        top = a.top + a.height / 2 - h / 2;
        left = a.right + gap;
        break;
      default:
        top = a.top - h - gap;
        left = a.left + a.width / 2 - w / 2;
    }

    const pad = 8;
    left = Math.max(pad, Math.min(left, window.innerWidth - w - pad));
    top = Math.max(pad, Math.min(top, window.innerHeight - h - pad));
    setCoords({ top, left });
  }, [open, side, maxWidth]);

  return (
    <>
      <span
        ref={anchorRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        aria-describedby={open ? id : undefined}
        className={cn('inline-flex', className)}
      >
        {children}
      </span>

      {open &&
        createPortal(
          <AnimatePresence>
            <motion.div
              ref={bubbleRef}
              id={id}
              role="tooltip"
              initial={{ opacity: 0, y: side === 'top' ? 4 : -4, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.14, ease: [0.22, 1, 0.36, 1] }}
              style={{
                position: 'fixed',
                top: coords?.top ?? -9999,
                left: coords?.left ?? -9999,
                maxWidth,
                zIndex: 9999,
              }}
              className="pointer-events-none rounded-md border border-line-bright bg-surface-3 px-2.5 py-1.5 text-xs leading-snug text-ink-2 shadow-pop"
            >
              {content}
            </motion.div>
          </AnimatePresence>,
          document.body,
        )}
    </>
  );
}

/**
 * A small "?" that carries a hint. Use beside a heading or metric label where
 * the term itself needs explaining.
 */
export function HelpDot({
  content,
  side = 'top',
  className,
}: {
  content: React.ReactNode;
  side?: Side;
  className?: string;
}) {
  return (
    <Hint content={content} side={side} delay={200}>
      <button
        type="button"
        aria-label="What is this?"
        className={cn(
          'inline-flex h-3.5 w-3.5 items-center justify-center rounded-full',
          'text-ink-4 transition-colors hover:text-hivis focus-visible:text-hivis',
          className,
        )}
      >
        <HelpCircle className="h-3.5 w-3.5" strokeWidth={2} />
      </button>
    </Hint>
  );
}

/* --------------------------------------------------------------------------
 * Shared copy.
 *
 * Kept in one place so the same term is never explained two different ways in
 * two different screens — which is how a glossary quietly starts contradicting
 * itself.
 * ----------------------------------------------------------------------- */

export const HINTS = {
  precursor:
    'A situation that could credibly have killed someone — judged on the energy present, the barrier state and who was exposed, not on whether anyone was actually hurt.',
  bucketPriority:
    'Strong, consistent evidence of a precursor. Goes to the top of the HSE queue.',
  bucketReview:
    'A genuine candidate, but some evidence is unverified. A person checks it.',
  bucketIncomplete:
    'The report does not say enough to decide. Sent back as a report-quality gap rather than guessed at.',
  bucketCleared:
    'Positive evidence against a precursor: low energy, nobody exposed, or a confirmed engineering barrier.',
  barrierGap:
    'How badly the safety control failed. Absent = 1.0, unverified = 0.6, confirmed = 0.0. An unmentioned barrier is never scored as present.',
  density:
    'Share of reports at a site that carry fatal potential. A site with 50 reports that all show confirmed barriers is safer than one with 10 where six show none.',
  compositeMetric:
    'Blends precursor rate, barrier-gap severity, energy magnitude and pattern recurrence, and damps sites that simply report more. Weights are equal and NOT calibrated yet.',
  simpleMetric:
    'Plain ratio of flagged reports to total reports. Transparent, but a site with a good reporting culture looks worse than one that stays quiet.',
  cusum:
    'A control chart. It signals when the reported precursor rate rises unusually above its own baseline. It detects a change in REPORTING, not a coming fatality.',
  cluster:
    'Reports grouped by the situation the engine extracted rather than by wording, so the same barrier failure described ten different ways lands in one pattern.',
  emerging:
    'A pattern concentrated in the most recent weeks rather than spread across the year — something that has started happening lately.',
  lsr:
    'The IOGP Life-Saving Rule that applies. Assigned by looking up the extracted energy type in a fixed table, not guessed by a model.',
  evidenceStrength:
    'How much the extracted evidence supports the verdict — combining energy certainty, barrier gap severity and how direct the exposure was.',
  recompute:
    'Re-runs the clustering job over all stored reports. Clustering is a batch job, so new reports appear in patterns only after this runs.',
  hierarchyOfControls:
    'Engineering fixes outrank procedures, which outrank training. Recommendations are ordered by this, from a fixed human-written library.',
  spans:
    'The exact words in the report that drove each part of the decision. Hover a colour in the legend to isolate it.',
  syntheticBanner:
    'This corpus is generated for the prototype. It is not Oil India data, and the banner stays up so no screenshot can imply otherwise.',
} as const;
