"use client";

import { useAuth } from "@/lib/api/auth-store";
import { ROLE_LABEL } from "@/lib/rbac";
import type { Role } from "@/lib/api/schemas";

export function RoleChip() {
  const { session, signOut } = useAuth();
  if (!session) return null;
  const role = session.role as Role;

  return (
    <div className="flex shrink-0 items-center gap-2 text-xs sm:gap-3">
      <span className="whitespace-nowrap border border-steel-fg/40 px-2 py-[3px] uppercase tracking-[0.06em] text-steel-fg">
        {ROLE_LABEL[role] ?? role}
      </span>
      <span className="hidden text-steel-fg/70 lg:inline">
        {session.username}
      </span>
      <button
        type="button"
        onClick={signOut}
        className="whitespace-nowrap border border-transparent px-1 py-[3px] uppercase tracking-[0.06em] text-steel-fg/80 hover:text-steel-fg focus-visible:border-focus sm:px-2"
      >
        Sign out
      </button>
    </div>
  );
}
