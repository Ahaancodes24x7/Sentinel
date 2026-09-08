/**
 * Fixtures for the SIF Action Center endpoints (recommendations, action plans,
 * impact) in NEXT_PUBLIC_USE_MOCKS mode.
 *
 * The `disclaimer` and `expected_objective` strings are fixed backend template
 * text — reproduced here verbatim, never reworded.
 */

export const IMPACT_DISCLAIMER =
  "Reported precursor frequency change following the intervention. " +
  "Historical association only — not a causal claim.";

export const RECOMMENDATION_LIST = [
  {
    pattern_id: "c17",
    title: "Energy Isolation Failure",
    evidence_summary: { report_count: 18, site_count: 4, window_days: 42, trend_pct: 45.0 },
    primary_barrier_failure: "Isolation verification",
    priority: "HIGH",
  },
  {
    pattern_id: "c18",
    title: "Confined Space Entry Protocol Violation",
    evidence_summary: { report_count: 6, site_count: 2, window_days: 42, trend_pct: 15.0 },
    primary_barrier_failure: "Gas testing re-verification",
    priority: "HIGH",
  },
  {
    pattern_id: "c19",
    title: "Fall-from-Height Permit Gap",
    evidence_summary: { report_count: 3, site_count: 1, window_days: 42, trend_pct: 4.0 },
    primary_barrier_failure: "Permit-to-work sighting",
    priority: "MEDIUM",
  },
  {
    pattern_id: "c20",
    title: "Personnel Under Suspended Load",
    evidence_summary: { report_count: 4, site_count: 2, window_days: 42, trend_pct: -15.0 },
    primary_barrier_failure: "Exclusion zone enforcement",
    priority: "MEDIUM",
  },
];

type Detail = {
  pattern_id: string;
  title: string;
  evidence: {
    report_count: number;
    site_count: number;
    window_days: number;
    member_report_ids: string[];
    breakdown: Record<string, number>;
    sites: string[];
  };
  recommended_interventions: {
    rank: number;
    control_level: string;
    priority: string;
    action: string;
  }[];
  expected_objective: string;
};

export const RECOMMENDATION_DETAIL: Record<string, Detail> = {
  c17: {
    pattern_id: "c17",
    title: "Energy Isolation Failure",
    evidence: {
      report_count: 18,
      site_count: 4,
      window_days: 42,
      member_report_ids: ["r-4401", "r-4410", "cx-201", "cx-202", "cx-203"],
      breakdown: {
        mentions_missing_isolation: 14,
        involves_maintenance: 11,
        involves_equipment_opening: 8,
      },
      sites: ["Rig 4", "Rig 7", "Plant C", "Well Site B"],
    },
    recommended_interventions: [
      { rank: 1, control_level: "administrative", priority: "HIGH", action: "Mandatory isolation verification checkpoint" },
      { rank: 2, control_level: "administrative", priority: "HIGH", action: "Supervisor PTW closure/start checkpoint" },
      { rank: 3, control_level: "training", priority: "MEDIUM", action: "Targeted Energy Isolation toolbox campaign" },
    ],
    expected_objective:
      "Reduce recurrence of reports involving unverified energy isolation.",
  },
  c18: {
    pattern_id: "c18",
    title: "Confined Space Entry Protocol Violation",
    evidence: {
      report_count: 6,
      site_count: 2,
      window_days: 42,
      member_report_ids: ["r-4406", "r-4412", "cx-210", "cx-211"],
      breakdown: {
        mentions_missing_isolation: 2,
        involves_maintenance: 4,
        involves_equipment_opening: 5,
      },
      sites: ["Well Site B", "Plant C"],
    },
    recommended_interventions: [
      { rank: 1, control_level: "engineering", priority: "HIGH", action: "Continuous atmospheric monitoring with entry interlock" },
      { rank: 2, control_level: "administrative", priority: "HIGH", action: "Re-test gas immediately before every entry, logged by the attendant" },
      { rank: 3, control_level: "training", priority: "MEDIUM", action: "Confined-space attendant refresher for named crews" },
    ],
    expected_objective:
      "Reduce recurrence of reports involving unverified confined-space atmosphere.",
  },
  c19: {
    pattern_id: "c19",
    title: "Fall-from-Height Permit Gap",
    evidence: {
      report_count: 3,
      site_count: 1,
      window_days: 42,
      member_report_ids: ["r-4405", "cx-220", "cx-221"],
      breakdown: {
        mentions_missing_isolation: 0,
        involves_maintenance: 1,
        involves_equipment_opening: 0,
      },
      sites: ["Field Station 2"],
    },
    recommended_interventions: [
      { rank: 1, control_level: "administrative", priority: "HIGH", action: "Permit sighting required at the work front before access" },
      { rank: 2, control_level: "training", priority: "MEDIUM", action: "Scaffold-access briefing for the Field Station 2 crew" },
    ],
    expected_objective:
      "Reduce recurrence of reports involving work at height without a sighted permit.",
  },
  c20: {
    pattern_id: "c20",
    title: "Personnel Under Suspended Load",
    evidence: {
      report_count: 4,
      site_count: 2,
      window_days: 42,
      member_report_ids: ["r-4413", "cx-230", "cx-231", "cx-232"],
      breakdown: {
        mentions_missing_isolation: 0,
        involves_maintenance: 2,
        involves_equipment_opening: 1,
      },
      sites: ["Terminal A", "Plant C"],
    },
    recommended_interventions: [
      { rank: 1, control_level: "engineering", priority: "HIGH", action: "Physical barriered exclusion zone under all lifts" },
      { rank: 2, control_level: "administrative", priority: "MEDIUM", action: "Spotter assigned to keep the drop zone clear" },
    ],
    expected_objective:
      "Reduce recurrence of reports involving personnel positioned under a suspended load.",
  },
};

/* ---- action plans: in-memory session store ------------------------------- */

export interface StoredPlan {
  action_plan_id: string;
  pattern_id: string;
  selected_intervention_ranks: number[];
  target_sites: string[];
  planned_start_date: string;
  actual_start_date?: string | null;
  status: string;
  seeded?: boolean;
}

export const ACTION_PLANS: Record<string, StoredPlan> = {
  ap_seed01: {
    action_plan_id: "ap_seed01",
    pattern_id: "c17",
    selected_intervention_ranks: [1, 2],
    target_sites: ["Rig 4"],
    planned_start_date: "2026-07-14",
    actual_start_date: "2026-07-15",
    status: "in_progress",
    seeded: true,
  },
};

export function impactFor(planId: string) {
  const plan = ACTION_PLANS[planId];
  const seeded = plan?.seeded;
  return {
    action_plan_id: planId,
    pattern_id: plan?.pattern_id ?? "c17",
    intervention_start_date:
      plan?.actual_start_date ?? plan?.planned_start_date ?? "2026-07-15",
    before: { window_days: 42, precursor_rate: 0.184 },
    after_weekly: seeded
      ? [
          { week: 1, precursor_rate: 0.179 },
          { week: 2, precursor_rate: 0.142 },
          { week: 3, precursor_rate: 0.108 },
          { week: 4, precursor_rate: 0.101 },
        ]
      : [],
    pct_change: seeded ? -41.3 : 0,
    disclaimer: IMPACT_DISCLAIMER,
  };
}
