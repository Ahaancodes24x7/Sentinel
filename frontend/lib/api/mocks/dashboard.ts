/**
 * Fixtures for the dashboard endpoints (rankings / clusters / trends / summary)
 * in NEXT_PUBLIC_USE_MOCKS mode. Vocabulary from aiml/configs/ontology.yaml.
 */

export const RANKINGS_BY_SITE = [
  { group: "Rig 4", sif_flagged_count: 18, total_reports: 98, density: 0.184, trend_direction: "up", trend_pct: 45.0, primary_lsr: "Energy Isolation" },
  { group: "Rig 7", sif_flagged_count: 11, total_reports: 74, density: 0.149, trend_direction: "up", trend_pct: 18.0, primary_lsr: "Hot Work" },
  { group: "Well Site B", sif_flagged_count: 7, total_reports: 63, density: 0.111, trend_direction: "flat", trend_pct: 3.0, primary_lsr: "Confined Space" },
  { group: "Field Station 2", sif_flagged_count: 5, total_reports: 68, density: 0.074, trend_direction: "down", trend_pct: -22.0, primary_lsr: "Working at Height" },
  { group: "Plant C", sif_flagged_count: 3, total_reports: 71, density: 0.042, trend_direction: "flat", trend_pct: 2.0, primary_lsr: "Safe Mechanical Lifting" },
  { group: "Terminal A", sif_flagged_count: 2, total_reports: 55, density: 0.036, trend_direction: "down", trend_pct: -8.0, primary_lsr: "Driving" },
];

export const RANKINGS_BY_ACTIVITY = [
  { group: "maintenance on process equipment", sif_flagged_count: 15, total_reports: 71, density: 0.211, trend_direction: "up", trend_pct: 52.0, primary_lsr: "Energy Isolation" },
  { group: "confined space entry for tank cleaning", sif_flagged_count: 8, total_reports: 44, density: 0.182, trend_direction: "up", trend_pct: 12.0, primary_lsr: "Confined Space" },
  { group: "hot work / welding near process line", sif_flagged_count: 9, total_reports: 58, density: 0.155, trend_direction: "flat", trend_pct: -1.0, primary_lsr: "Hot Work" },
  { group: "lifting operation with mobile crane", sif_flagged_count: 6, total_reports: 62, density: 0.097, trend_direction: "down", trend_pct: -15.0, primary_lsr: "Safe Mechanical Lifting" },
  { group: "scaffolding erection at height", sif_flagged_count: 4, total_reports: 51, density: 0.078, trend_direction: "flat", trend_pct: 4.0, primary_lsr: "Working at Height" },
  { group: "routine equipment inspection", sif_flagged_count: 1, total_reports: 66, density: 0.015, trend_direction: "down", trend_pct: -30.0, primary_lsr: "Work Authorisation" },
];

export const METRIC_WEIGHTS = {
  w1_severity_adjusted_rate: 0.34,
  w2_recurrence: 0.33,
  w3_severity_weighting: 0.33,
};

/* ------------------------------------------------------------------ clusters */

export const CLUSTERS = [
  {
    cluster_id: "c17",
    pattern_summary:
      "Energy Isolation | stored/electrical energy | uncertain isolation verification",
    member_report_ids: ["r-4401", "r-4410", "cx-201", "cx-202", "cx-203", "cx-204"],
    member_count: 18,
    sites: ["Rig 4", "Rig 7", "Plant C", "Well Site B"],
    primary_lsr: "Energy Isolation",
    pattern_type: "established",
  },
  {
    cluster_id: "c18",
    pattern_summary:
      "Confined Space | atmospheric/asphyxiation | gas test not re-verified before entry",
    member_report_ids: ["r-4406", "r-4412", "cx-210", "cx-211", "cx-212"],
    member_count: 6,
    sites: ["Well Site B", "Plant C"],
    primary_lsr: "Confined Space",
    pattern_type: "emerging",
  },
  {
    cluster_id: "c19",
    pattern_summary:
      "Working at Height | fall from height | no permit sighted, first-aid outcome",
    member_report_ids: ["r-4405", "cx-220", "cx-221"],
    member_count: 3,
    sites: ["Field Station 2"],
    primary_lsr: "Working at Height",
    pattern_type: "sporadic_high_severity",
  },
  {
    cluster_id: "c20",
    pattern_summary:
      "Safe Mechanical Lifting | gravitational (suspended load) | worker under load",
    member_report_ids: ["r-4413", "cx-230", "cx-231", "cx-232"],
    member_count: 4,
    sites: ["Terminal A", "Plant C"],
    primary_lsr: "Safe Mechanical Lifting",
    pattern_type: "emerging",
  },
];

// Edges connect individual member report ids (per the backend response shape),
// not cluster nodes.
export const CLUSTER_EDGES = [
  { source: "r-4401", target: "r-4410", similarity: 0.88 },
  { source: "r-4410", target: "cx-201", similarity: 0.84 },
  { source: "cx-201", target: "cx-202", similarity: 0.9 },
  { source: "cx-202", target: "cx-203", similarity: 0.79 },
  { source: "r-4406", target: "r-4412", similarity: 0.86 },
  { source: "r-4412", target: "cx-210", similarity: 0.81 },
  { source: "cx-210", target: "cx-211", similarity: 0.77 },
  { source: "r-4405", target: "cx-220", similarity: 0.83 },
  { source: "cx-220", target: "cx-221", similarity: 0.8 },
  { source: "r-4413", target: "cx-230", similarity: 0.85 },
  { source: "cx-230", target: "cx-231", similarity: 0.78 },
];

/* ------------------------------------------------------------------ trends */

export function trendSeries(granularity: string, site?: string, lsr?: string) {
  // Weekly base series with a clear ramp + one CUSUM alert near the end.
  const weekly = [
    { period: "2026-07-06", count: 3 },
    { period: "2026-07-13", count: 4 },
    { period: "2026-07-20", count: 4 },
    { period: "2026-07-27", count: 6 },
    { period: "2026-08-03", count: 5 },
    { period: "2026-08-10", count: 7 },
    { period: "2026-08-17", count: 15 },
    { period: "2026-08-24", count: 13 },
    { period: "2026-08-31", count: 11 },
  ];
  const scale = site ? 0.5 : 1;
  const scaled = weekly.map((p) => ({
    period: p.period,
    count: Math.max(0, Math.round(p.count * scale * (lsr ? 0.6 : 1))),
  }));

  if (granularity === "monthly") {
    const byMonth: Record<string, number> = {};
    for (const p of scaled) {
      const m = p.period.slice(0, 7) + "-01";
      byMonth[m] = (byMonth[m] ?? 0) + p.count;
    }
    return {
      series: Object.entries(byMonth).map(([period, count]) => ({ period, count })),
      alerts: [] as { period: string; message: string; method: string }[],
    };
  }

  const alerts =
    !site && !lsr
      ? [
          {
            period: "2026-08-17",
            message:
              "Unusual increase in reported precursor rate — investigate.",
            method: "CUSUM",
          },
        ]
      : [];
  return { series: scaled, alerts };
}

/* ------------------------------------------------------------------ summary */

export const DASHBOARD_SUMMARY = {
  total_reports: 2184,
  high_priority_pattern_count: 4,
  reports_pending_review: 6,
  last_ingested_at: "2026-09-05T06:00:00Z",
};
