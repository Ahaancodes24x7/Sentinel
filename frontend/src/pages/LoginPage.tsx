import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Activity, ArrowRight, LoaderCircle } from 'lucide-react';
import { api, ROLE_KEY, TOKEN_KEY, USER_KEY, ApiError } from '../api/client';
import { PulseDot } from '../components/kinetic';
import { cn } from '../lib/cn';

const DEMO_ACCOUNTS = [
  { username: 'manager_demo', role: 'HSE Manager', detail: 'Full access · can ingest and plan' },
  { username: 'hse_demo', role: 'HSE Reviewer', detail: 'Triage and correct classifications' },
  { username: 'auditor_demo', role: 'Auditor', detail: 'Read-only, audit trail access' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard';

  const [username, setUsername] = useState('manager_demo');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<{ access_token: string; role: string }>('/auth/login', {
        username,
        password,
      });
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(ROLE_KEY, res.role);
      localStorage.setItem(USER_KEY, username);
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.offline
          ? 'Cannot reach the Sentinel API — start the backend on port 8000.'
          : 'Invalid username or password.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="field-grid scanlines relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-6">
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="drift absolute left-1/4 top-0 h-[34rem] w-[34rem] rounded-full bg-hivis/[0.06] blur-[120px]" />
        <div
          className="drift absolute bottom-0 right-1/4 h-[28rem] w-[28rem] rounded-full bg-info/[0.05] blur-[120px]"
          style={{ animationDelay: '-8s' }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 w-full max-w-4xl"
      >
        <div className="grid overflow-hidden rounded-lg border border-line bg-surface/80 shadow-pop backdrop-blur-xl md:grid-cols-2">
          {/* Left: identity */}
          <div className="relative border-b border-line p-8 md:border-b-0 md:border-r">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-hivis">
                <Activity className="h-4.5 w-4.5 text-on-hivis" strokeWidth={2.75} />
              </div>
              <div>
                <div className="font-display text-2xl leading-none text-ink">SENTINEL</div>
                <div className="font-mono text-[9px] tracked text-ink-4">PS 26165 · OIL INDIA</div>
              </div>
            </div>

            <h1 className="mt-8 font-display text-4xl leading-[0.95] text-ink">
              Fatal potential,
              <br />
              <span className="text-hivis">before the fatality.</span>
            </h1>

            <p className="mt-4 text-sm leading-relaxed text-ink-3">
              An AI/NLP engine that reads free-text HSSE observations and infers whether the
              situation described carried credible fatal potential — independent of whether anyone
              was actually hurt.
            </p>

            <div className="mt-6 space-y-2">
              {[
                'Energy · barrier · exposure extracted as evidence',
                'Mapped to IOGP Life-Saving Rules by ontology lookup',
                'Recall-optimised routing with human review',
              ].map((line) => (
                <div key={line} className="flex items-center gap-2">
                  <PulseDot tone="hivis" size={5} live={false} />
                  <span className="text-xs text-ink-2">{line}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: form */}
          <div className="p-8">
            <div className="font-mono text-2xs tracked text-ink-4">AUTHENTICATE</div>

            <form onSubmit={submit} className="mt-4 space-y-3">
              <div>
                <label className="font-mono text-[9px] tracked text-ink-4">USERNAME</label>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  className="mt-1 w-full rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-hivis-edge focus:outline-none"
                />
              </div>
              <div>
                <label className="font-mono text-[9px] tracked text-ink-4">PASSWORD</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="mt-1 w-full rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:border-hivis-edge focus:outline-none"
                />
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-md border border-critical-edge bg-critical-wash px-3 py-2 text-xs text-critical"
                >
                  {error}
                </motion.div>
              )}

              <button
                type="submit"
                disabled={busy}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-md bg-hivis px-4 py-2.5',
                  'font-mono text-2xs tracked text-on-hivis transition-transform',
                  'hover:scale-[1.01] disabled:opacity-60',
                )}
              >
                {busy ? (
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
                )}
                {busy ? 'AUTHENTICATING' : 'ENTER CONSOLE'}
              </button>
            </form>

            <div className="mt-6 border-t border-line pt-4">
              <div className="font-mono text-[9px] tracked text-ink-4">DEMO ACCOUNTS</div>
              <div className="mt-2 space-y-1.5">
                {DEMO_ACCOUNTS.map((acct) => (
                  <button
                    key={acct.username}
                    type="button"
                    onClick={() => {
                      setUsername(acct.username);
                      setPassword('demo123');
                    }}
                    className="flex w-full items-center gap-2 rounded-md border border-line bg-surface-2 px-2.5 py-1.5 text-left transition-colors hover:border-hivis-edge"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-2xs text-ink">{acct.username}</div>
                      <div className="text-[10px] text-ink-4">{acct.detail}</div>
                    </div>
                    <span className="shrink-0 font-mono text-[9px] tracked text-hivis">
                      {acct.role}
                    </span>
                  </button>
                ))}
              </div>
              <p className="mt-3 text-[10px] leading-relaxed text-ink-4">
                Three hardcoded demo accounts, deliberately. A real deployment would federate to
                OIL&rsquo;s identity provider — building user management here would not have been a
                good use of prototype time.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
