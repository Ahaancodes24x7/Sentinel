import Link from "next/link";

export function CtaBlock() {
  return (
    <section className="border-t border-line bg-steel text-steel-fg">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 px-4 py-14 sm:px-6 md:flex-row md:items-center md:justify-between md:py-16">
        <div>
          <h2 className="text-xl font-bold tracking-tight md:text-2xl">
            Get into the console
          </h2>
          <p className="mt-2 max-w-xl text-sm text-steel-fg/75">
            Access is provisioned per person against a role. Request it below, or
            sign in if you already have an account.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/signup"
            className="bg-surface px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.06em] text-ink hover:opacity-90"
          >
            Request access
          </Link>
          <Link
            href="/login"
            className="border border-steel-fg/40 px-5 py-2.5 text-sm font-semibold uppercase tracking-[0.06em] text-steel-fg hover:border-steel-fg"
          >
            Sign in
          </Link>
        </div>
      </div>
    </section>
  );
}
