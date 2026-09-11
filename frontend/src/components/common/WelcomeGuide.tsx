/**
 * First-screen orientation shown right after login. Sentinel has a lot of
 * surface area (six analysis screens plus camera monitoring plus a map) and
 * most of it is domain jargon — this walks a new viewer through what each
 * part of the console actually does before they start clicking around.
 *
 * Content is generated from `SECTIONS` in Sidebar.tsx rather than duplicated
 * here, so the guide can never drift out of sync with the real nav.
 */
import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, MapPin, Wifi, X } from 'lucide-react';
import { SentinelLogo } from './SentinelMark';
import { SECTIONS } from '../layout/Sidebar';
import { cn } from '../../lib/cn';

const SKIP_KEY = 'sentinel_skip_welcome';

export function shouldShowWelcomeGuide() {
  try {
    return localStorage.getItem(SKIP_KEY) !== '1';
  } catch {
    return true;
  }
}

export function WelcomeGuide({ onClose }: { onClose: () => void }) {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  function close() {
    try {
      if (dontShowAgain) localStorage.setItem(SKIP_KEY, '1');
    } catch {
      /* private-browsing localStorage can throw — the guide just reappears next login */
    }
    onClose();
  }

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-void/80 p-4 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.25 }}
        onClick={close}
      >
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Welcome to Sentinel"
          className="relative flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-line bg-surface shadow-pop"
          initial={{ opacity: 0, y: 16, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.98 }}
          transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative shrink-0 border-b border-line bg-surface-2/60 px-6 py-5">
            <button
              type="button"
              onClick={close}
              aria-label="Close"
              className="absolute right-4 top-4 rounded-sm p-1.5 text-ink-3 transition-colors hover:bg-surface-3 hover:text-ink"
            >
              <X className="h-4 w-4" strokeWidth={2} />
            </button>
            <SentinelLogo size={30} />
            <h1 className="mt-4 font-display text-2xl text-ink">Welcome to Sentinel</h1>
            <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-ink-3">
              An AI/NLP engine that reads free-text HSSE observations and infers whether the
              situation described carried credible fatal potential, plus a live computer-vision
              watch over camera feeds. Here is what each part of the console does.
            </p>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex items-start gap-2.5 rounded-md border border-line bg-surface-2 px-3 py-2.5">
                <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-hivis" strokeWidth={2.2} />
                <p className="text-xs leading-relaxed text-ink-2">
                  <span className="font-medium text-ink">Site selector</span> — top bar, scopes
                  every screen (reports, patterns, camera list, map) to one OIL India site:
                  Duliajan, Digboi or Moran.
                </p>
              </div>
              <div className="flex items-start gap-2.5 rounded-md border border-line bg-surface-2 px-3 py-2.5">
                <Wifi className="mt-0.5 h-3.5 w-3.5 shrink-0 text-hivis" strokeWidth={2.2} />
                <p className="text-xs leading-relaxed text-ink-2">
                  <span className="font-medium text-ink">Engine status</span> — top left, shows
                  whether the analysis backend is reachable. Nothing on screen refreshes while it
                  reads offline.
                </p>
              </div>
            </div>

            {SECTIONS.map((section) => (
              <div key={section.title} className="mb-5 last:mb-0">
                <div className="mb-2 font-mono text-[10px] tracked text-ink-4">{section.title}</div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {section.items.map((item) => (
                    <div
                      key={item.to}
                      className="flex items-start gap-2.5 rounded-md border border-line bg-surface-2 px-3 py-2.5"
                    >
                      <item.icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-3" strokeWidth={1.9} />
                      <div className="min-w-0">
                        <div className="text-xs font-medium text-ink">{item.label}</div>
                        <p className="mt-0.5 text-[11px] leading-relaxed text-ink-3">{item.hint}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="flex shrink-0 items-center justify-between gap-3 border-t border-line bg-surface-2/60 px-6 py-4">
            <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-3">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => setDontShowAgain(e.target.checked)}
                className="h-3.5 w-3.5 cursor-pointer accent-hivis"
              />
              Don&rsquo;t show this again
            </label>
            <button
              type="button"
              onClick={close}
              className={cn(
                'flex items-center gap-2 rounded-md bg-hivis px-4 py-2',
                'font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.02]',
              )}
            >
              Start exploring
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
