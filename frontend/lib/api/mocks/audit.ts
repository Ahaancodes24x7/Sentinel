/**
 * Audit-log fixtures for NEXT_PUBLIC_USE_MOCKS mode. A spread of entity types
 * and actions across a few actors, newest first.
 */
export interface AuditRow {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  timestamp: string;
}

export const AUDIT_LOG: AuditRow[] = [
  { id: "al_0031", entity_type: "action_plan", entity_id: "ap_2201", action: "created", actor: "manager_demo", timestamp: "2026-09-05T09:14:00Z" },
  { id: "al_0030", entity_type: "review_action", entity_id: "r-4412", action: "correct", actor: "reviewer_2", timestamp: "2026-09-05T08:52:00Z" },
  { id: "al_0029", entity_type: "review_action", entity_id: "r-4412", action: "correct", actor: "hse_demo", timestamp: "2026-09-04T16:03:00Z" },
  { id: "al_0028", entity_type: "report", entity_id: "batch_9f2e1a", action: "ingested", actor: "manager_demo", timestamp: "2026-09-05T06:00:00Z" },
  { id: "al_0027", entity_type: "review_action", entity_id: "r-4403", action: "confirm", actor: "hse_demo", timestamp: "2026-09-03T11:20:00Z" },
  { id: "al_0026", entity_type: "action_plan", entity_id: "ap_seed01", action: "status_changed", actor: "manager_demo", timestamp: "2026-07-15T07:30:00Z" },
  { id: "al_0025", entity_type: "action_plan", entity_id: "ap_seed01", action: "created", actor: "manager_demo", timestamp: "2026-07-12T13:45:00Z" },
  { id: "al_0024", entity_type: "review_action", entity_id: "r-4405", action: "reject", actor: "hse_demo", timestamp: "2026-07-10T10:05:00Z" },
  { id: "al_0023", entity_type: "report", entity_id: "batch_71aa02", action: "ingested", actor: "manager_demo", timestamp: "2026-07-01T06:00:00Z" },
  { id: "al_0022", entity_type: "review_action", entity_id: "r-4410", action: "correct", actor: "reviewer_2", timestamp: "2026-06-28T14:12:00Z" },
];
