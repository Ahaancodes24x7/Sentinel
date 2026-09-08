"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRole } from "@/lib/api/auth-store";
import { can, type Capability } from "@/lib/rbac";

interface NavItem {
  href: string;
  label: string;
  cap: Capability;
  status: "live" | "next"; // "next" = lands in a later build pass
}

const ITEMS: NavItem[] = [
  { href: "/reports", label: "Reports", cap: "view_reports", status: "live" },
  {
    href: "/review-queue",
    label: "Review queue",
    cap: "view_review_queue",
    status: "live",
  },
  { href: "/rankings", label: "Rankings", cap: "view_rankings", status: "live" },
  { href: "/clusters", label: "Clusters", cap: "view_clusters", status: "live" },
  { href: "/trends", label: "Trends", cap: "view_trends", status: "live" },
  {
    href: "/action-center",
    label: "Action center",
    cap: "view_action_center",
    status: "live",
  },
  {
    href: "/audit-log",
    label: "Audit log",
    cap: "view_audit_log",
    status: "live",
  },
];

export function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const role = useRole();

  const visible = ITEMS.filter((i) => can(role, i.cap));

  return (
    <nav className="flex flex-col gap-px" aria-label="Primary">
      {visible.map((item) => {
        const active = pathname.startsWith(item.href);
        const disabled = item.status === "next";
        const className = `flex items-center justify-between border-l-2 px-3 py-2 text-sm ${
          active
            ? "border-l-focus bg-surface font-semibold text-ink"
            : "border-l-transparent text-muted hover:bg-surface hover:text-ink"
        } ${disabled ? "cursor-not-allowed opacity-55" : ""}`;

        if (disabled) {
          return (
            <span
              key={item.href}
              className={className}
              aria-disabled
              title="Lands in a later build pass"
            >
              {item.label}
              <span className="label !text-[0.5625rem]">soon</span>
            </span>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={className}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
