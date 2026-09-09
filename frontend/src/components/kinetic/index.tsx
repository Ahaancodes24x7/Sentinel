/**
 * Kinetic primitives.
 *
 * The console is meant to look like it is running, so these are the pieces
 * that move: numbers that count rather than snap, status dots that breathe,
 * bars that fill, feeds that push new rows in from the top.
 *
 * Every one of them also encodes its state statically (colour, text, width),
 * so under `prefers-reduced-motion` — where index.css disables the animation —
 * nothing becomes unreadable or ambiguous. Motion here is emphasis, never the
 * only carrier of meaning.
 */

import { useEffect, useRef, useState } from 'react';
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from 'framer-motion';
import { cn } from '../../lib/cn';

export type Tone =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'info'
  | 'violet'
  | 'hivis'
  | 'neutral';

export const TONE_TEXT: Record<Tone, string> = {
  critical: 'text-critical',
  high: 'text-high',
  medium: 'text-medium',
  low: 'text-low',
  info: 'text-info',
  violet: 'text-violet',
  hivis: 'text-hivis',
  neutral: 'text-ink-3',
};

export const TONE_BG: Record<Tone, string> = {
  critical: 'bg-critical',
  high: 'bg-high',
  medium: 'bg-medium',
  low: 'bg-low',
  info: 'bg-info',
  violet: 'bg-violet',
  hivis: 'bg-hivis',
  neutral: 'bg-ink-4',
};

export const TONE_CHIP: Record<Tone, string> = {
  critical: 'bg-critical-wash text-critical border-critical-edge',
  high: 'bg-high-wash text-high border-high-edge',
  medium: 'bg-medium-wash text-medium border-medium-edge',
  low: 'bg-low-wash text-low border-low-edge',
  info: 'bg-info-wash text-info border-info-edge',
  violet: 'bg-violet-wash text-violet border-violet/40',
  hivis: 'bg-hivis-wash text-hivis border-hivis-edge',
  neutral: 'bg-surface-3 text-ink-2 border-line-bright',
};

/* ========================================================================== */

interface CounterProps {
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
  /** Duration of the count-up, in seconds. */
  duration?: number;
}

/**
 * A number that counts to its value and flashes when it changes.
 *
 * The flash is the important part: on a screen someone glances at every few
 * minutes, a silently-updated figure is indistinguishable from a stale one.
 */
export function Counter({
  value,
  decimals = 0,
  suffix = '',
  prefix = '',
  className,
  duration = 0.9,
}: CounterProps) {
  const reduced = useReducedMotion();
  const motionValue = useMotionValue(reduced ? value : 0);
  const spring = useSpring(motionValue, {
    duration: duration * 1000,
    bounce: 0,
  });
  const display = useTransform(spring, (latest) =>
    `${prefix}${latest.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}${suffix}`,
  );

  const previous = useRef(value);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    motionValue.set(value);
    if (previous.current !== value) {
      previous.current = value;
      setFlash(true);
      const timer = setTimeout(() => setFlash(false), 900);
      return () => clearTimeout(timer);
    }
  }, [value, motionValue]);

  return (
    <motion.span className={cn('tabular', flash && 'flash-up', className)}>
      {display}
    </motion.span>
  );
}

/* ========================================================================== */

/** Breathing status dot. The halo only animates when `live` is set. */
export function PulseDot({
  tone = 'hivis',
  live = true,
  size = 8,
  className,
}: {
  tone?: Tone;
  live?: boolean;
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={cn('relative inline-flex shrink-0', TONE_TEXT[tone], className)}
      style={{ width: size, height: size }}
    >
      {live && <span className="pulse-ring absolute inset-0 rounded-full opacity-70" />}
      <span
        className={cn('relative rounded-full', TONE_BG[tone])}
        style={{ width: size, height: size }}
      />
    </span>
  );
}

/* ========================================================================== */

/** Small uppercase chip. The workhorse label of the whole interface. */
export function Chip({
  tone = 'neutral',
  children,
  className,
  dot = false,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5',
        'font-mono text-2xs tracked font-medium whitespace-nowrap',
        TONE_CHIP[tone],
        className,
      )}
    >
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', TONE_BG[tone])} />}
      {children}
    </span>
  );
}

/* ========================================================================== */

/** Horizontal magnitude bar that animates to width on mount and on change. */
export function Bar({
  value,
  tone = 'hivis',
  height = 4,
  className,
  delay = 0,
}: {
  value: number; // 0..1
  tone?: Tone;
  height?: number;
  className?: string;
  delay?: number;
}) {
  const pct = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)) * 100;
  return (
    <div
      className={cn('w-full overflow-hidden rounded-full bg-surface-3', className)}
      style={{ height }}
      role="presentation"
    >
      <motion.div
        className={cn('h-full rounded-full', TONE_BG[tone])}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

/* ========================================================================== */

/**
 * Sparkline. Draws itself on with a path-length animation, and optionally
 * marks alert points — used for the CUSUM signals on the trend charts.
 */
export function Sparkline({
  values,
  tone = 'hivis',
  height = 36,
  alerts = [],
  className,
}: {
  values: number[];
  tone?: Tone;
  height?: number;
  alerts?: number[];
  className?: string;
}) {
  const reduced = useReducedMotion();
  if (!values.length) {
    return <div className={cn('w-full', className)} style={{ height }} />;
  }

  const width = 240;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : width;

  const points = values.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2]);
  const d = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${d} L${width},${height} L0,${height} Z`;

  const stroke = `var(--color-${tone === 'neutral' ? 'ink-3' : tone})`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={cn('w-full', className)}
      style={{ height }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`spark-${tone}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#spark-${tone})`} />
      <motion.path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        initial={reduced ? undefined : { pathLength: 0 }}
        animate={reduced ? undefined : { pathLength: 1 }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
      />
      {alerts.map((idx) =>
        points[idx] ? (
          <circle
            key={idx}
            cx={points[idx][0]}
            cy={points[idx][1]}
            r="2.5"
            fill="var(--color-critical)"
            stroke="var(--color-bg)"
            strokeWidth="1"
          />
        ) : null,
      )}
    </svg>
  );
}

/* ========================================================================== */

/** Panel with a sweeping scan line in its top edge — the "monitoring" tell. */
export function ScanPanel({
  children,
  className,
  active = true,
}: {
  children: React.ReactNode;
  className?: string;
  active?: boolean;
}) {
  return (
    <div className={cn('panel scan-sweep edge-top relative', className)}>
      {active && <span className="scan-bar" />}
      {children}
    </div>
  );
}

/* ========================================================================== */

/** Section header used across every screen. */
export function PanelHead({
  title,
  sub,
  right,
  tone = 'hivis',
  className,
}: {
  title: string;
  sub?: string;
  right?: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 border-b border-line px-4 py-3',
        className,
      )}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('h-3 w-0.5 rounded-full', TONE_BG[tone])} />
          <h2 className="font-mono text-2xs tracked text-ink-2">{title}</h2>
        </div>
        {sub && <p className="mt-1 pl-3.5 text-xs text-ink-3">{sub}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

/* ========================================================================== */

/**
 * Live feed. New items animate in from the top and push the rest down; the
 * list is capped so it behaves like a rolling tail rather than growing forever.
 */
export function LiveFeed<T>({
  items,
  renderItem,
  keyFor,
  max = 8,
  className,
}: {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  keyFor: (item: T) => string;
  max?: number;
  className?: string;
}) {
  const visible = items.slice(0, max);
  return (
    <div className={cn('divide-y divide-line-faint', className)}>
      <AnimatePresence initial={false} mode="popLayout">
        {visible.map((item, i) => (
          <motion.div
            key={keyFor(item)}
            layout
            initial={{ opacity: 0, y: -14, backgroundColor: 'rgba(212,255,63,0.10)' }}
            animate={{ opacity: 1, y: 0, backgroundColor: 'rgba(212,255,63,0)' }}
            exit={{ opacity: 0, height: 0, marginTop: 0, marginBottom: 0 }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          >
            {renderItem(item, i)}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/* ========================================================================== */

/** Indeterminate loading rail — honest about "working", unlike a fake %. */
export function LoadingRail({ className }: { className?: string }) {
  return (
    <div className={cn('h-0.5 w-full overflow-hidden bg-surface-3', className)}>
      <div className="rail-bar h-full w-1/4 bg-hivis" />
    </div>
  );
}

/** Skeleton block for content that has not arrived yet. */
export function Shimmer({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn('rounded-sm bg-surface-2', className)}
      animate={{ opacity: [0.45, 0.85, 0.45] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

/* ========================================================================== */

/** Staggered entrance wrapper for grids and lists. */
export function Stagger({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.05, delayChildren: delay } },
      }}
    >
      {children}
    </motion.div>
  );
}

export const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const } },
};

export function StaggerItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div variants={staggerItem} className={className}>
      {children}
    </motion.div>
  );
}

/* ========================================================================== */

/** A clock that actually ticks. Small detail; large effect on "is this live?". */
export function LiveClock({ className }: { className?: string }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <span className={cn('font-mono text-2xs tabular text-ink-3', className)}>
      {now.toISOString().slice(11, 19)} UTC
    </span>
  );
}
