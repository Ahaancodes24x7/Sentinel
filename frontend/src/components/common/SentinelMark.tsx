/**
 * The Sentinel brand mark: a 270° ring left open at the top, with a fixed
 * point sitting in the gap. Read as "the system watching, with the signal
 * marked at the point it hasn't closed on yet" — a detection mark, not a
 * decorative glyph. Geometry only, no font rendering, so it stays identical
 * at favicon size and at hero size.
 *
 * The ring uses currentColor so it can sit in muted ink in the console chrome
 * and brighter ink on the landing page; the point is always hi-vis — it is
 * the one thing in the mark that is ever allowed to be the accent colour.
 */
import { cn } from '../../lib/cn';

export function SentinelMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={cn('shrink-0', className)}
      role="img"
      aria-label="Sentinel"
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="7" fill="var(--color-void)" stroke="var(--color-line-bright)" />
      <path
        d="M23.07 8.93 A10 10 0 1 1 8.93 8.93"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="6" r="2.2" fill="var(--color-hivis)" />
    </svg>
  );
}

/** Mark + wordmark lockup, used in the nav and console sidebar. */
export function SentinelLogo({
  caption,
  size = 28,
  className,
}: {
  caption?: string;
  size?: number;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <SentinelMark size={size} className="text-ink-2" />
      <div className="min-w-0 leading-none">
        <div className="font-display text-lg leading-none text-ink">SENTINEL</div>
        {caption && <div className="mt-1 font-mono text-[9px] tracked text-ink-4">{caption}</div>}
      </div>
    </div>
  );
}
