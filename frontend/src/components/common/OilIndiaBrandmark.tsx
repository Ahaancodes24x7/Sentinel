/**
 * OIL India lockup for the landing page header — an evocative badge (ring +
 * drop icon, Devanagari + English wordmark, tagline), not a pixel-exact
 * reproduction of the corporate trademark. Used once, top-right of the hero.
 */
import { cn } from '../../lib/cn';

export function OilIndiaBrandmark({ className }: { className?: string }) {
  return (
    <div className={cn('flex flex-col items-end', className)}>
      <div className="flex items-center gap-2.5">
        <svg width="32" height="32" viewBox="0 0 24 24" className="shrink-0" aria-hidden="true">
          <circle cx="12" cy="12" r="10.4" fill="none" stroke="#F2F5F8" strokeWidth="1.4" />
          <circle cx="12" cy="7.6" r="1.6" fill="#F2F5F8" />
          <rect x="10.2" y="10.6" width="3.6" height="8.2" rx="1.8" fill="#E4362B" />
        </svg>
        <div className="text-left leading-tight">
          <div className="font-sans text-[15px] font-semibold text-ink">ऑयल इंडिया</div>
          <div className="font-display text-lg leading-none text-ink">OIL INDIA</div>
        </div>
      </div>
      <div className="mt-1.5 font-mono text-[9px] uppercase tracking-[0.22em] text-ink-3">
        Energy for a safer tomorrow
      </div>
    </div>
  );
}
