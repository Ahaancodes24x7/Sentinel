/**
 * Thin typed wrappers over apiFetch. One function per backend endpoint.
 * Only the endpoints needed for the foundation pass are implemented; the rest
 * carry a signature + TODO so later passes are additive.
 */
import { apiFetch } from "./client";
import {
  LoginResponseSchema,
  MeResponseSchema,
  ReportDetailSchema,
  PaginatedReportsSchema,
  ReviewActionResponseSchema,
  RankingsResponseSchema,
  ClustersResponseSchema,
  TrendsResponseSchema,
  DashboardSummarySchema,
  RecommendationsResponseSchema,
  RecommendationDetailSchema,
  ActionPlanResponseSchema,
  ImpactResponseSchema,
  PaginatedAuditLogSchema,
  type LoginResponse,
  type MeResponse,
  type ReportDetail,
  type PaginatedReports,
  type ReviewActionRequest,
  type ReviewActionResponse,
  type RankingsResponse,
  type ClustersResponse,
  type TrendsResponse,
  type DashboardSummary,
  type RecommendationsResponse,
  type RecommendationDetail,
  type ActionPlanRequest,
  type ActionPlanResponse,
  type ActionPlanUpdateRequest,
  type ImpactResponse,
  type PaginatedAuditLog,
} from "./schemas";

export function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  return apiFetch("/auth/login", {
    schema: LoginResponseSchema,
    method: "POST",
    body: { username, password },
    auth: false,
  });
}

export function me(): Promise<MeResponse> {
  return apiFetch("/auth/me", { schema: MeResponseSchema });
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return apiFetch(`/reports/${encodeURIComponent(reportId)}`, {
    schema: ReportDetailSchema,
  });
}

export interface ReportFilters {
  site?: string;
  sif_potential?: boolean;
  bucket?: string;
  lsr_tag?: string;
  date_from?: string;
  date_to?: string;
  source?: string;
  limit?: number;
  offset?: number;
}

export function listReports(
  filters: ReportFilters = {}
): Promise<PaginatedReports> {
  return apiFetch("/reports", {
    schema: PaginatedReportsSchema,
    query: filters as Record<string, string | number | boolean | undefined>,
  });
}

/* ------------------------------------------------------------------ *
 * Review queue
 * ------------------------------------------------------------------ */

export interface ReviewQueueParams {
  site?: string;
  sort?: "oldest" | "newest" | "confidence_asc";
  limit?: number;
  offset?: number;
}

export function getReviewQueue(
  params: ReviewQueueParams = {}
): Promise<PaginatedReports> {
  return apiFetch("/review-queue", {
    schema: PaginatedReportsSchema,
    query: params as Record<string, string | number | undefined>,
  });
}

export function submitReviewAction(
  reportId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return apiFetch(`/review-queue/${encodeURIComponent(reportId)}/action`, {
    schema: ReviewActionResponseSchema,
    method: "POST",
    body,
  });
}

/* ------------------------------------------------------------------ *
 * Dashboard
 * ------------------------------------------------------------------ */

export interface RankingParams {
  metric?: "simple" | "composite";
  group_by?: "site" | "activity";
  window_days?: number;
}

export function getRankings(
  params: RankingParams = {}
): Promise<RankingsResponse> {
  return apiFetch("/dashboard/rankings", {
    schema: RankingsResponseSchema,
    query: params as Record<string, string | number | undefined>,
  });
}

export function getClusters(
  params: { site?: string; min_cluster_size?: number } = {}
): Promise<ClustersResponse> {
  return apiFetch("/dashboard/clusters", {
    schema: ClustersResponseSchema,
    query: params as Record<string, string | number | undefined>,
  });
}

export function getTrends(
  params: {
    site?: string;
    lsr_tag?: string;
    granularity?: "weekly" | "monthly";
  } = {}
): Promise<TrendsResponse> {
  return apiFetch("/dashboard/trends", {
    schema: TrendsResponseSchema,
    query: params as Record<string, string | undefined>,
  });
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch("/dashboard/summary", { schema: DashboardSummarySchema });
}

/* ------------------------------------------------------------------ *
 * Recommendations / action plans / impact
 * ------------------------------------------------------------------ */

export function listRecommendations(): Promise<RecommendationsResponse> {
  return apiFetch("/recommendations", {
    schema: RecommendationsResponseSchema,
  });
}

export function getRecommendation(
  patternId: string
): Promise<RecommendationDetail> {
  return apiFetch(`/recommendations/${encodeURIComponent(patternId)}`, {
    schema: RecommendationDetailSchema,
  });
}

export function createActionPlan(
  patternId: string,
  body: ActionPlanRequest
): Promise<ActionPlanResponse> {
  return apiFetch(
    `/recommendations/${encodeURIComponent(patternId)}/action-plan`,
    { schema: ActionPlanResponseSchema, method: "POST", body }
  );
}

export function updateActionPlan(
  actionPlanId: string,
  body: ActionPlanUpdateRequest
): Promise<ActionPlanResponse> {
  return apiFetch(`/action-plans/${encodeURIComponent(actionPlanId)}`, {
    schema: ActionPlanResponseSchema,
    method: "PATCH",
    body,
  });
}

export function getActionPlanImpact(
  actionPlanId: string
): Promise<ImpactResponse> {
  return apiFetch(
    `/action-plans/${encodeURIComponent(actionPlanId)}/impact`,
    { schema: ImpactResponseSchema }
  );
}

/* ------------------------------------------------------------------ *
 * Audit log
 * ------------------------------------------------------------------ */

export interface AuditLogParams {
  entity_type?: string;
  entity_id?: string;
  actor?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export function getAuditLog(
  params: AuditLogParams = {}
): Promise<PaginatedAuditLog> {
  return apiFetch("/audit-log", {
    schema: PaginatedAuditLogSchema,
    query: params as Record<string, string | number | undefined>,
  });
}
