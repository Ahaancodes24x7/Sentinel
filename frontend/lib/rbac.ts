/**
 * Role -> capability map. Nav and available actions are derived from this,
 * not hidden with CSS. Mirrors the role gates in backend/main.py:
 *  - ingest / create action plan / patch action plan : hse_manager only
 *  - review-queue actions : hse_reviewer + hse_manager
 *  - audit-log : auditor + hse_manager
 */
import type { Role } from "./api/schemas";

export type Capability =
  | "view_reports"
  | "view_review_queue"
  | "act_review_queue"
  | "ingest_data"
  | "view_rankings"
  | "view_clusters"
  | "view_trends"
  | "view_action_center"
  | "create_action_plan"
  | "view_audit_log";

const MATRIX: Record<Role, Capability[]> = {
  hse_reviewer: [
    "view_reports",
    "view_review_queue",
    "act_review_queue",
    "view_rankings",
    "view_clusters",
    "view_trends",
    "view_action_center",
  ],
  hse_manager: [
    "view_reports",
    "view_review_queue",
    "act_review_queue",
    "ingest_data",
    "view_rankings",
    "view_clusters",
    "view_trends",
    "view_action_center",
    "create_action_plan",
    "view_audit_log",
  ],
  // Auditor sees everything read-only (matches the backend, which only gates
  // review-queue actions, ingestion, action-plan writes, and the audit log).
  auditor: [
    "view_reports",
    "view_rankings",
    "view_clusters",
    "view_trends",
    "view_action_center",
    "view_audit_log",
  ],
};

export function can(role: Role | null, cap: Capability): boolean {
  if (!role) return false;
  return MATRIX[role]?.includes(cap) ?? false;
}

export const ROLE_LABEL: Record<Role, string> = {
  hse_reviewer: "HSE Reviewer",
  hse_manager: "HSE Manager",
  auditor: "Auditor",
};
