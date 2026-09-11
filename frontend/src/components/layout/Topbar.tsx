import { useNavigate } from 'react-router-dom';
import { AlertTriangle, LogOut, MapPin, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/cn';
import { Chip, LiveClock, PulseDot } from '../kinetic';
import { Hint, HINTS } from '../common/Hint';
import { useHealth, useRecomputePatterns, useTrends } from '../../api/hooks';
import { clearSession } from '../../api/client';
import { useSelectedSite } from '../../lib/siteContext';

/**
 * The synthetic-data banner is permanent and non-dismissible by design.
 *
 * The research blueprint is blunt about this: presenting synthetic reports as
 * though they were OIL production data is the fastest way to lose credibility
 * in a Q&A. So the provenance is stated on every screen, at the top, where it
 * cannot be missed or scrolled past.
 */
function ProvenanceBanner() {
  return (
    <Hint content={HINTS.syntheticBanner} side="bottom">
      <div className="flex w-full items-center gap-2 border-b border-medium-edge bg-medium-wash px-4 py-1">
        <AlertTriangle className="h-3 w-3 shrink-0 text-medium" strokeWidth={2.2} />
        <span className="font-mono text-2xs tracked text-medium">
          SYNTHETIC DEMONSTRATION DATASET — NOT OIL PRODUCTION DATA
        </span>
      </div>
    </Hint>
  );
}

/** Scrolling alert ticker fed by real CUSUM/EWMA signals. */
function AlertTicker() {
  const { data, isLoading } = useTrends();
  const alerts = data?.alerts ?? [];

  // "No signals" and "not loaded yet" must not look identical - one is an
  // all-clear, the other is an absence of information.
  if (isLoading && !data) {
    return (
      <div className="flex items-center gap-2 text-ink-4">
        <PulseDot tone="info" size={6} />
        <span className="font-mono text-2xs tracked">LOADING CONTROL CHART…</span>
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div className="flex items-center gap-2 text-ink-4">
        <PulseDot tone="low" size={6} />
        <span className="font-mono text-2xs tracked">NO ACTIVE SPC SIGNALS</span>
      </div>
    );
  }

  const strip = alerts.slice(-6);
  return (
    <div className="relative flex-1 overflow-hidden">
      <div className="marquee-track gap-8">
        {[0, 1].map((copy) => (
          <span key={copy} className="flex shrink-0 items-center gap-8 pr-8">
            {strip.map((alert, i) => (
              <span key={`${copy}-${i}`} className="flex items-center gap-2 whitespace-nowrap">
                <PulseDot tone={alert.severity === 'high' ? 'critical' : 'high'} size={6} />
                <span className="font-mono text-2xs tracked text-ink-2">
                  {alert.period} · {alert.method}
                </span>
                <span className="text-xs text-ink-3">{alert.message}</span>
              </span>
            ))}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Site selector.
 *
 * The demo now spans three real OIL India locations. Switching here drives
 * the Camera Watch camera list directly; other screens keep their own
 * independent site filters (which cover the full registry, not just these
 * three) so this selector never silently narrows data someone didn't ask to
 * filter.
 */
function SiteSelector() {
  const { selectedSite, setSelectedSiteId, sites } = useSelectedSite();
  return (
    <Hint
      content="Active OIL India site for this demo. Drives the camera list on Camera Watch."
      side="bottom"
    >
      <div className="flex items-center gap-1.5 rounded-sm border border-line-bright px-2 py-1 text-ink-2">
        <MapPin className="h-3 w-3 text-hivis" strokeWidth={2.2} />
        <select
          value={selectedSite.site_id}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="cursor-pointer bg-transparent font-mono text-2xs tracked text-ink outline-none"
        >
          {sites.map((s) => (
            <option key={s.site_id} value={s.site_id} className="bg-surface text-ink">
              {s.canonical_name.toUpperCase()}
            </option>
          ))}
        </select>
      </div>
    </Hint>
  );
}

export function Topbar() {
  const navigate = useNavigate();
  const { data: health, isError } = useHealth();
  const recompute = useRecomputePatterns();

  const online = !isError && health?.status === 'ok';
  const role = typeof window !== 'undefined' ? localStorage.getItem('sentinel_role') : null;
  const username = typeof window !== 'undefined' ? localStorage.getItem('sentinel_user') : null;

  function signOut() {
    clearSession();
    navigate('/login', { replace: true });
  }

  return (
    <header className="relative z-20 shrink-0 border-b border-line bg-surface/70 backdrop-blur-xl">
      <ProvenanceBanner />

      <div className="flex h-12 items-center gap-4 px-4">
        {/* Connection state — never ambiguous */}
        <Hint
          content={
            online
              ? 'The analysis engine is reachable and responding. Everything on screen is live data.'
              : 'The backend is not responding. Nothing on screen is being refreshed — start the API on port 8000.'
          }
          side="bottom"
        >
        <div
          className={cn(
            'flex items-center gap-2 rounded-sm border px-2 py-1',
            online
              ? 'border-hivis-edge bg-hivis-wash text-hivis'
              : 'border-critical-edge bg-critical-wash text-critical',
          )}
        >
          {online ? (
            <Wifi className="h-3 w-3" strokeWidth={2.2} />
          ) : (
            <WifiOff className="h-3 w-3 blink" strokeWidth={2.2} />
          )}
          <span className="font-mono text-2xs tracked">
            {online ? 'ENGINE LIVE' : 'ENGINE OFFLINE'}
          </span>
        </div>
        </Hint>

        {health?.model_version && (
          <Hint content="Version of the model currently making these decisions." side="bottom">
            <Chip tone="neutral">{health.model_version}</Chip>
          </Hint>
        )}

        <SiteSelector />

        <div className="mx-2 h-4 w-px bg-line" />

        <AlertTicker />

        <div className="ml-auto flex items-center gap-3">
          <LiveClock />

          <Hint content={HINTS.recompute} side="bottom">
          <button
            type="button"
            onClick={() => recompute.mutate()}
            disabled={recompute.isPending}
            className="flex items-center gap-1.5 rounded-sm border border-line-bright px-2 py-1 text-ink-2 transition-colors hover:border-hivis-edge hover:text-hivis disabled:opacity-50"
          >
            <motion.span
              animate={recompute.isPending ? { rotate: 360 } : { rotate: 0 }}
              transition={
                recompute.isPending
                  ? { duration: 1, repeat: Infinity, ease: 'linear' }
                  : { duration: 0.2 }
              }
              className="inline-flex"
            >
              <RefreshCw className="h-3 w-3" strokeWidth={2.2} />
            </motion.span>
            <span className="font-mono text-2xs tracked">
              {recompute.isPending ? 'CLUSTERING' : 'RECOMPUTE'}
            </span>
          </button>
          </Hint>

          <div className="flex items-center gap-2 border-l border-line pl-3">
            <div className="text-right">
              <div className="text-xs leading-tight text-ink">{username ?? 'demo'}</div>
              <div className="font-mono text-[9px] tracked text-ink-4">
                {(role ?? 'hse_reviewer').replace(/_/g, ' ')}
              </div>
            </div>
            <button
              type="button"
              onClick={signOut}
              title="Sign out"
              className="rounded-sm p-1.5 text-ink-3 transition-colors hover:bg-surface-3 hover:text-critical"
            >
              <LogOut className="h-3.5 w-3.5" strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
