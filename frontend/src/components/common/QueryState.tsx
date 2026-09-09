/**
 * Shared loading / error / empty states.
 *
 * The error state deliberately distinguishes "the backend is unreachable" from
 * "the backend said no". With no mock fallback behind it any more, this is the
 * only thing standing between a disconnected console and a blank screen the
 * user cannot interpret — so it tells them exactly what broke and what to do.
 */

import { AlertOctagon, DatabaseZap, Inbox, PlugZap } from 'lucide-react';
import { cn } from '../../lib/cn';
import { LoadingRail, Shimmer } from '../kinetic';
import { ApiError } from '../../api/client';

export function PanelLoading({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn('space-y-2 p-4', className)}>
      <LoadingRail className="mb-3" />
      {Array.from({ length: rows }).map((_, i) => (
        <Shimmer key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

export function QueryError({
  error,
  className,
  compact = false,
}: {
  error: unknown;
  className?: string;
  compact?: boolean;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const offline = apiError?.offline ?? false;

  const Icon = offline ? PlugZap : AlertOctagon;
  const title = offline ? 'Sentinel engine unreachable' : 'Request failed';
  const message = offline
    ? 'The API is not responding. Start the backend, then this panel will recover on its own.'
    : (apiError?.message ?? 'Something went wrong loading this panel.');

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2 px-4 py-3 text-critical', className)}>
        <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
        <span className="font-mono text-2xs tracked">{title}</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-panel border border-critical-edge bg-critical-wash px-6 py-10 text-center',
        className,
      )}
    >
      <Icon className="h-6 w-6 text-critical" strokeWidth={1.8} />
      <div className="font-mono text-2xs tracked text-critical">{title}</div>
      <p className="max-w-sm text-xs text-ink-3">{message}</p>
      {offline && (
        <code className="mt-1 rounded-sm bg-void px-2 py-1 font-mono text-2xs text-ink-3">
          uvicorn backend.main:app --port 8000
        </code>
      )}
    </div>
  );
}

export function EmptyPanel({
  title = 'Nothing here yet',
  message,
  icon: Icon = Inbox,
  className,
}: {
  title?: string;
  message?: string;
  icon?: typeof Inbox;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 px-6 py-12 text-center',
        className,
      )}
    >
      <Icon className="h-6 w-6 text-ink-4" strokeWidth={1.6} />
      <div className="font-mono text-2xs tracked text-ink-3">{title}</div>
      {message && <p className="max-w-sm text-xs text-ink-4">{message}</p>}
    </div>
  );
}

export function NoDataYet({ className }: { className?: string }) {
  return (
    <EmptyPanel
      icon={DatabaseZap}
      title="No reports ingested"
      message="Seed the database to populate the console: python -m backend.seed_database --reset"
      className={className}
    />
  );
}
