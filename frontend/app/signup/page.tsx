"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/api/auth-store";
import { ApiError } from "@/lib/api/errors";
import { requestAccess } from "@/lib/api/endpoints";
import { ROLE_LABEL } from "@/lib/rbac";
import type { Role } from "@/lib/api/schemas";
import { AuthScaffold } from "@/components/auth/AuthScaffold";
import { AuthField, AuthTextArea } from "@/components/auth/AuthField";
import { AuthAlert } from "@/components/auth/AuthAlert";
import { SubmitButton } from "@/components/auth/SubmitButton";

const ROLES: Role[] = ["hse_reviewer", "hse_manager", "auditor"];

interface Form {
  full_name: string;
  email: string;
  organisation: string;
  requested_role: Role;
  justification: string;
}

const EMPTY: Form = {
  full_name: "",
  email: "",
  organisation: "",
  requested_role: "hse_reviewer",
  justification: "",
};

type Errors = Partial<Record<keyof Form, string>>;

function validate(f: Form): Errors {
  const e: Errors = {};
  if (f.full_name.trim().length < 2) e.full_name = "Enter your full name.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim()))
    e.email = "Enter a valid work email.";
  if (f.organisation.trim().length < 2)
    e.organisation = "Enter your organisation or site.";
  if (f.justification.trim().length < 12)
    e.justification = "Add a sentence on why you need access.";
  return e;
}

export default function SignupPage() {
  const { session, ready } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<Form>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  useEffect(() => {
    if (ready && session) router.replace("/reports");
  }, [ready, session, router]);

  function set<K extends keyof Form>(key: K, value: Form[K]) {
    const next = { ...form, [key]: value };
    setForm(next);
    if (touched) setErrors(validate(next));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    setServerError(null);
    try {
      const res = await requestAccess({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        organisation: form.organisation.trim(),
        requested_role: form.requested_role,
        justification: form.justification.trim(),
      });
      setReference(res.reference);
    } catch (err) {
      setServerError(
        err instanceof ApiError
          ? err.message
          : "Could not submit the request. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  if (reference) {
    return (
      <AuthScaffold
        heading="Request received"
        intro="An HSE administrator provisions console accounts by hand — you'll get an email when yours is live."
        footer={
          <Link
            href="/login"
            className="font-semibold text-focus hover:underline"
          >
            Back to sign in
          </Link>
        }
      >
        <AuthAlert tone="clear" title="Pending approval">
          Reference <span className="font-mono">{reference}</span> — keep this
          for follow-up.
        </AuthAlert>
        <dl className="mt-4 space-y-2 border border-line bg-surface p-4 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Name</dt>
            <dd className="text-ink">{form.full_name}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Email</dt>
            <dd className="font-mono text-ink">{form.email}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Organisation</dt>
            <dd className="text-ink">{form.organisation}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Requested role</dt>
            <dd className="text-ink">{ROLE_LABEL[form.requested_role]}</dd>
          </div>
        </dl>
      </AuthScaffold>
    );
  }

  return (
    <AuthScaffold
      heading="Request access"
      intro="Console accounts are provisioned per person against a role. Tell us who you are and what you need."
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-focus hover:underline"
          >
            Sign in
          </Link>
          .
        </>
      }
    >
      <form onSubmit={submit} className="space-y-3" noValidate>
        <AuthField
          label="Full name"
          value={form.full_name}
          autoComplete="name"
          onChange={(e) => set("full_name", e.target.value)}
          error={errors.full_name}
        />
        <AuthField
          label="Work email"
          type="email"
          value={form.email}
          autoComplete="email"
          onChange={(e) => set("email", e.target.value)}
          error={errors.email}
        />
        <AuthField
          label="Organisation / site"
          value={form.organisation}
          autoComplete="organization"
          onChange={(e) => set("organisation", e.target.value)}
          error={errors.organisation}
        />

        <label className="block">
          <span className="label">Requested role</span>
          <select
            value={form.requested_role}
            onChange={(e) => set("requested_role", e.target.value as Role)}
            className="mt-1 w-full border border-line bg-surface px-3 py-2 font-mono text-sm outline-none focus-visible:border-focus"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-2xs text-muted">
            Reviewer: review queue + classifications. Manager: adds ingest,
            action plans, audit log. Auditor: read-only + audit log.
          </span>
        </label>

        <AuthTextArea
          label="Why do you need access?"
          rows={3}
          value={form.justification}
          onChange={(e) => set("justification", e.target.value)}
          error={errors.justification}
          hint="One or two sentences — your team, and what you'll use Sentinel for."
        />

        {serverError && <AuthAlert title="Request failed">{serverError}</AuthAlert>}

        <SubmitButton busy={busy} busyLabel="Submitting…" type="submit">
          Submit request
        </SubmitButton>
        <p className="text-2xs text-muted">
          No password is set here. Access is granted by an administrator; you set
          a password on first sign-in.
        </p>
      </form>
    </AuthScaffold>
  );
}
