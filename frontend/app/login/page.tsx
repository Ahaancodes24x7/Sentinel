"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/api/auth-store";
import { USE_MOCKS } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { AuthScaffold } from "@/components/auth/AuthScaffold";
import { AuthField } from "@/components/auth/AuthField";
import { AuthAlert } from "@/components/auth/AuthAlert";
import { SubmitButton } from "@/components/auth/SubmitButton";

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
    <AuthScaffold
      heading="Sign in"
      intro="Enter your Sentinel console credentials."
      footer={
        <>
          Need an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-focus hover:underline"
          >
            Request access
          </Link>
          .
        </>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(username, password);
        }}
        className="space-y-3"
      >
        <AuthField
          label="Username"
          value={username}
          autoComplete="username"
          onChange={(e) => setUsername(e.target.value)}
        />
        <AuthField
          label="Password"
          type="password"
          value={password}
          autoComplete="current-password"
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <AuthAlert title="Sign-in failed">{error}</AuthAlert>}

        <SubmitButton busy={busy} busyLabel="Signing in…" type="submit">
          Sign in
        </SubmitButton>
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
            backend. Set{" "}
            <code className="font-mono">NEXT_PUBLIC_USE_MOCKS=false</code> to use
            the live API.
          </p>
        )}
      </div>
    </AuthScaffold>
  );
}
