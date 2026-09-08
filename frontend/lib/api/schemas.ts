/**
 * Zod schemas mirroring backend/schemas.py field-for-field.
 * These are the single typed contract every screen consumes.
 *
 * Defensive choices (see plan / backend notes):
 *  - `ExtractedFields` is `.passthrough()` and every span field is nullable+optional.
 *  - `hazard` is a union of the *correct* span shape and the *buggy* pipeline shape
 *    (`{label, confidence, span}`) so neither the current bug nor a future fix breaks
 *    the client.
 *  - `span` is `[start, end] | null`.
 */
import { z } from "zod";

export const BucketSchema = z.enum([
  "HIGH_CONF_SIF",
  "LOW_CONF_REVIEW",
  "HIGH_CONF_NON_SIF",
  "NEEDS_MORE_INFO",
]);
export type Bucket = z.infer<typeof BucketSchema>;

export const SourceSchema = z.enum(["synthetic", "real"]);
export type Source = z.infer<typeof SourceSchema>;

export const RoleSchema = z.enum(["hse_reviewer", "hse_manager", "auditor"]);
export type Role = z.infer<typeof RoleSchema>;

export const ReviewActionTypeSchema = z.enum(["confirm", "correct", "reject"]);
export type ReviewActionType = z.infer<typeof ReviewActionTypeSchema>;

export const PatternTypeSchema = z.enum([
  "established",
  "emerging",
  "sporadic_high_severity",
]);
export type PatternType = z.infer<typeof PatternTypeSchema>;

const conf = z.number().min(0).max(1);
export const SpanSchema = z
  .tuple([z.number(), z.number()])
  .nullable()
  .optional();

export const ExtractedSpanFieldSchema = z
  .object({
    text: z.string(),
    span: SpanSchema,
    confidence: conf,
  })
  .passthrough();
export type ExtractedSpanField = z.infer<typeof ExtractedSpanFieldSchema>;

export const ExtractedLabelFieldSchema = z
  .object({
    label: z.string(),
    confidence: conf,
    span: SpanSchema,
  })
  .passthrough();
export type ExtractedLabelField = z.infer<typeof ExtractedLabelFieldSchema>;

/** The shape sif_engine/pipeline.py currently emits for `hazard` (the bug). */
export const BuggyHazardFieldSchema = z
  .object({
    label: z.string(),
    confidence: conf,
    span: SpanSchema,
  })
  .passthrough();

export const HazardFieldSchema = z.union([
  ExtractedSpanFieldSchema,
  BuggyHazardFieldSchema,
]);
export type HazardField = z.infer<typeof HazardFieldSchema>;

export const EvidenceSpanItemSchema = z
  .object({
    field: z.string(),
    text: z.string(),
    span: z.tuple([z.number(), z.number()]),
    confidence: conf.default(1),
  })
  .passthrough();
export type EvidenceSpanItem = z.infer<typeof EvidenceSpanItemSchema>;

export const ExtractedFieldsSchema = z
  .object({
    activity: ExtractedSpanFieldSchema,
    hazard: HazardFieldSchema.nullable().optional(),
    energy_type: ExtractedLabelFieldSchema,
    exposure: ExtractedLabelFieldSchema,
    barrier: ExtractedSpanFieldSchema.nullable().optional(),
    barrier_status: ExtractedLabelFieldSchema,
    location: ExtractedSpanFieldSchema.nullable().optional(),
    evidence_spans: z.array(EvidenceSpanItemSchema).optional().default([]),
  })
  .passthrough();
export type ExtractedFields = z.infer<typeof ExtractedFieldsSchema>;

export const ClassificationSchema = z
  .object({
    sif_potential: z.boolean(),
    confidence: conf,
    bucket: BucketSchema,
    lsr_tag: z.string(),
    justification: z.string(),
    model_version: z.string(),
  })
  .passthrough();
export type Classification = z.infer<typeof ClassificationSchema>;

export const ReportDetailSchema = z
  .object({
    report_id: z.string(),
    site: z.string(),
    timestamp: z.string(),
    source: SourceSchema,
    report_text: z.string(),
    extracted_fields: ExtractedFieldsSchema,
    classification: ClassificationSchema,
    review_status: z.string(),
  })
  .passthrough();
export type ReportDetail = z.infer<typeof ReportDetailSchema>;

export const ReportListItemSchema = z.object({
  report_id: z.string(),
  site: z.string(),
  timestamp: z.string(),
  sif_potential: z.boolean(),
  bucket: BucketSchema,
  lsr_tag: z.string(),
});
export type ReportListItem = z.infer<typeof ReportListItemSchema>;

export const PaginatedReportsSchema = z.object({
  items: z.array(ReportListItemSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});
export type PaginatedReports = z.infer<typeof PaginatedReportsSchema>;

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  role: RoleSchema,
});
export type LoginResponse = z.infer<typeof LoginResponseSchema>;

export const MeResponseSchema = z.object({
  username: z.string(),
  role: RoleSchema,
});
export type MeResponse = z.infer<typeof MeResponseSchema>;

/* ------------------------------------------------------------------ *
 * Review queue — GET /review-queue (PaginatedReports shape) +
 * POST /review-queue/{report_id}/action
 * ------------------------------------------------------------------ */

export const ReviewActionRequestSchema = z.object({
  action: ReviewActionTypeSchema,
  corrected_sif_potential: z.boolean().nullable().optional(),
  corrected_lsr_tag: z.string().nullable().optional(),
  reviewer_notes: z.string().nullable().optional(),
});
export type ReviewActionRequest = z.infer<typeof ReviewActionRequestSchema>;

export const ReviewActionResponseSchema = z.object({
  report_id: z.string(),
  review_action_id: z.string(),
  status: z.string(),
  promoted_to_training_queue: z.boolean(),
});
export type ReviewActionResponse = z.infer<typeof ReviewActionResponseSchema>;

/* ------------------------------------------------------------------ *
 * Dashboard — rankings / clusters / trends / summary
 * ------------------------------------------------------------------ */

export const RankingRowSchema = z
  .object({
    group: z.string(),
    sif_flagged_count: z.number(),
    total_reports: z.number(),
    density: z.number(),
    trend_direction: z.string(), // "up" | "down" | "flat"
    trend_pct: z.number(),
    primary_lsr: z.string(),
  })
  .passthrough();
export type RankingRow = z.infer<typeof RankingRowSchema>;

export const MetricWeightsSchema = z
  .object({
    w1_severity_adjusted_rate: z.number(),
    w2_recurrence: z.number(),
    w3_severity_weighting: z.number(),
  })
  .passthrough();
export type MetricWeights = z.infer<typeof MetricWeightsSchema>;

export const RankingsResponseSchema = z.object({
  metric: z.string(),
  window_days: z.number(),
  rankings: z.array(RankingRowSchema),
  weights: MetricWeightsSchema.nullable().optional(),
});
export type RankingsResponse = z.infer<typeof RankingsResponseSchema>;

export const ClusterItemSchema = z
  .object({
    cluster_id: z.string(),
    pattern_summary: z.string(),
    member_report_ids: z.array(z.string()),
    member_count: z.number(),
    sites: z.array(z.string()),
    primary_lsr: z.string(),
    pattern_type: PatternTypeSchema,
  })
  .passthrough();
export type ClusterItem = z.infer<typeof ClusterItemSchema>;

export const ClusterEdgeSchema = z
  .object({
    source: z.string(),
    target: z.string(),
    similarity: z.number(),
  })
  .passthrough();
export type ClusterEdge = z.infer<typeof ClusterEdgeSchema>;

export const ClustersResponseSchema = z.object({
  clusters: z.array(ClusterItemSchema),
  edges: z.array(ClusterEdgeSchema),
});
export type ClustersResponse = z.infer<typeof ClustersResponseSchema>;

export const TrendPointSchema = z.object({
  period: z.string(),
  count: z.number(),
});
export type TrendPoint = z.infer<typeof TrendPointSchema>;

export const TrendAlertSchema = z
  .object({
    period: z.string(),
    message: z.string(),
    method: z.string(),
  })
  .passthrough();
export type TrendAlert = z.infer<typeof TrendAlertSchema>;

export const TrendsResponseSchema = z.object({
  series: z.array(TrendPointSchema),
  alerts: z.array(TrendAlertSchema),
});
export type TrendsResponse = z.infer<typeof TrendsResponseSchema>;

export const DashboardSummarySchema = z.object({
  total_reports: z.number(),
  high_priority_pattern_count: z.number(),
  reports_pending_review: z.number(),
  last_ingested_at: z.string(),
});
export type DashboardSummary = z.infer<typeof DashboardSummarySchema>;

/* ------------------------------------------------------------------ *
 * Recommendations / intervention engine / action plans / impact
 * ------------------------------------------------------------------ */

export const EvidenceSummarySchema = z
  .object({
    report_count: z.number(),
    site_count: z.number(),
    window_days: z.number(),
    trend_pct: z.number(),
  })
  .passthrough();

export const RecommendationListItemSchema = z
  .object({
    pattern_id: z.string(),
    title: z.string(),
    evidence_summary: EvidenceSummarySchema,
    primary_barrier_failure: z.string(),
    priority: z.string(), // HIGH | MEDIUM | LOW
  })
  .passthrough();
export type RecommendationListItem = z.infer<
  typeof RecommendationListItemSchema
>;

export const RecommendationsResponseSchema = z.object({
  recommendations: z.array(RecommendationListItemSchema),
});
export type RecommendationsResponse = z.infer<
  typeof RecommendationsResponseSchema
>;

export const EvidenceDetailSchema = z
  .object({
    report_count: z.number(),
    site_count: z.number(),
    window_days: z.number(),
    member_report_ids: z.array(z.string()),
    breakdown: z.record(z.string(), z.number()),
    sites: z.array(z.string()),
  })
  .passthrough();

export const RecommendedInterventionSchema = z
  .object({
    rank: z.number(),
    control_level: z.string(),
    priority: z.string(),
    action: z.string(),
  })
  .passthrough();
export type RecommendedIntervention = z.infer<
  typeof RecommendedInterventionSchema
>;

export const RecommendationDetailSchema = z
  .object({
    pattern_id: z.string(),
    title: z.string(),
    evidence: EvidenceDetailSchema,
    recommended_interventions: z.array(RecommendedInterventionSchema),
    expected_objective: z.string(),
  })
  .passthrough();
export type RecommendationDetail = z.infer<typeof RecommendationDetailSchema>;

export const ActionPlanRequestSchema = z.object({
  selected_intervention_ranks: z.array(z.number()),
  target_sites: z.array(z.string()),
  planned_start_date: z.string(), // ISO date
});
export type ActionPlanRequest = z.infer<typeof ActionPlanRequestSchema>;

export const ActionPlanResponseSchema = z
  .object({
    action_plan_id: z.string(),
    pattern_id: z.string(),
    status: z.string(),
  })
  .passthrough();
export type ActionPlanResponse = z.infer<typeof ActionPlanResponseSchema>;

export const ActionPlanUpdateRequestSchema = z.object({
  actual_start_date: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
});
export type ActionPlanUpdateRequest = z.infer<
  typeof ActionPlanUpdateRequestSchema
>;

export const ImpactResponseSchema = z.object({
  action_plan_id: z.string(),
  pattern_id: z.string(),
  intervention_start_date: z.string(),
  before: z.object({ window_days: z.number(), precursor_rate: z.number() }),
  after_weekly: z.array(
    z.object({ week: z.number(), precursor_rate: z.number() })
  ),
  pct_change: z.number(),
  disclaimer: z.string(),
});
export type ImpactResponse = z.infer<typeof ImpactResponseSchema>;

/* ------------------------------------------------------------------ *
 * Audit log
 * ------------------------------------------------------------------ */

export const AuditLogEntrySchema = z
  .object({
    id: z.string(),
    entity_type: z.string(),
    entity_id: z.string(),
    action: z.string(),
    actor: z.string(),
    timestamp: z.string(),
  })
  .passthrough();
export type AuditLogEntry = z.infer<typeof AuditLogEntrySchema>;

export const PaginatedAuditLogSchema = z.object({
  items: z.array(AuditLogEntrySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});
export type PaginatedAuditLog = z.infer<typeof PaginatedAuditLogSchema>;
