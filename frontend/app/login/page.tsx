"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/api/auth-store";
import { USE_MOCKS } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { Panel } from "@/components/ui/Panel";

const DEMO_ACCOUNTS = [
  { username: "manager_demo", role: "HSE Manager", note: "ingest, action plans, audit log" },
  { username: "hse_demo", role: "HSE Reviewer", note: "review queue, classifications" },
  { username: "auditor_demo", role: "Auditor", note: "read-only + audit log" },
];

export default function LoginPage() {
  const { session, ready, signIn } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("manager_demo");
  const [password, setPassword] = useState("demo123");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && session) router.replace("/reports");
  }, [ready, session, router]);

  async function submit(u: string, p: string) {
    setBusy(true);
    setError(null);
    try {
      await signIn(u, p);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Sign-in failed. Please try again."
      );
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-panel p-4">
      <div className="w-full max-w-md">
        <div className="mb-4 flex items-baseline gap-2">
          <span className="text-2xl font-bold uppercase tracking-[0.16em]">
            Sentinel
          </span>
          <span className="label">SIF Precursor Monitor</span>
        </div>

        <Panel title="Sign in">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(username, password);
            }}
            className="space-y-3"
          >
            <label className="block">
              <span className="label">Username</span>
              <input
                className="mt-1 w-full border border-line bg-surface px-3 py-2 font-mono text-sm focus-visible:border-focus"
                value={username}
                autoComplete="username"
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="label">Password</span>
              <input
                type="password"
                className="mt-1 w-full border border-line bg-surface px-3 py-2 font-mono text-sm focus-visible:border-focus"
                value={password}
                autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            {error && (
              <p
                role="alert"
                className="border-l-2 border-danger bg-danger/5 px-3 py-2 text-xs text-danger"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full bg-steel px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg disabled:opacity-60"
            >
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-5 border-t border-line pt-4">
            <p className="label mb-2">Demo accounts · password demo123</p>
            <ul className="space-y-1.5">
              {DEMO_ACCOUNTS.map((a) => (
                <li key={a.username}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setUsername(a.username);
                      setPassword("demo123");
                      submit(a.username, "demo123");
                    }}
                    className="flex w-full items-center justify-between border border-line bg-surface px-3 py-2 text-left hover:border-focus disabled:opacity-60"
                  >
                    <span>
                      <span className="text-sm font-semibold">{a.role}</span>
                      <span className="ml-2 font-mono text-xs text-muted">
                        {a.username}
                      </span>
                    </span>
                    <span className="hidden text-2xs text-muted sm:inline">
                      {a.note}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {USE_MOCKS && (
              <p className="mt-3 text-2xs text-muted">
                Offline demo mode is on — any demo account signs in without a
                backend. Set <code className="font-mono">NEXT_PUBLIC_USE_MOCKS=false</code>{" "}
                to use the live API.
              </p>
            )}
          </div>
        </Panel>
      </div>
    </main>
  );
}
