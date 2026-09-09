/**
 * Typed React Query hooks over the Sentinel API.
 *
 * Several of these poll. That is not decoration: this console is meant to be
 * left open on a control-room screen, and a precursor queue that only updates
 * when someone presses F5 is a queue nobody trusts. Polling intervals are
 * chosen per resource — the review queue and summary move often, the ontology
 * never does.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, qs } from './client';
import type {
  AssociationsResponse,
  AuditEntry,
  BarrierFailureRow,
  Bucket,
  ClustersResponse,
  DashboardSummary,
  HealthResponse,
  Ontology,
  Paginated,
  RankingsResponse,
  RecommendationDetail,
  RecommendationListItem,
  ReportDetail,
  ReportListItem,
  TrendsResponse,
} from './types';

/* -------------------------------------------------------------------------
 * Health / session
 * ---------------------------------------------------------------------- */

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthResponse>('/health'),
    refetchInterval: 15000,
    retry: 1,
    staleTime: 0,
  });
}

export function useOntology() {
  return useQuery({
    queryKey: ['ontology'],
    queryFn: () => api.get<Ontology>('/ontology'),
    staleTime: Infinity, // taxonomy is versioned config, not live data
  });
}

/* -------------------------------------------------------------------------
 * Dashboard
 * ---------------------------------------------------------------------- */

export function useSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => api.get<DashboardSummary>('/dashboard/summary'),
    refetchInterval: 12000,
  });
}

export function useRankings(metric: 'simple' | 'composite', groupBy: 'site' | 'activity' = 'site',
                            windowDays = 42) {
  return useQuery({
    queryKey: ['rankings', metric, groupBy, windowDays],
    queryFn: () =>
      api.get<RankingsResponse>(
        `/dashboard/rankings${qs({ metric, group_by: groupBy, window_days: windowDays })}`,
      ),
    refetchInterval: 30000,
  });
}

export function useClusters(site?: string, minClusterSize = 3) {
  return useQuery({
    queryKey: ['clusters', site, minClusterSize],
    queryFn: () =>
      api.get<ClustersResponse>(
        `/dashboard/clusters${qs({ site, min_cluster_size: minClusterSize })}`,
      ),
    staleTime: 60000,
  });
}

export function useTrends(site?: string, lsrTag?: string, granularity: 'weekly' | 'monthly' = 'weekly') {
  return useQuery({
    queryKey: ['trends', site, lsrTag, granularity],
    queryFn: () =>
      api.get<TrendsResponse>(`/dashboard/trends${qs({ site, lsr_tag: lsrTag, granularity })}`),
    refetchInterval: 45000,
  });
}

/* -------------------------------------------------------------------------
 * Reports
 * ---------------------------------------------------------------------- */

export interface ReportFilters {
  site?: string;
  bucket?: Bucket | string;
  lsr_tag?: string;
  sif_potential?: boolean;
  source?: string;
  limit?: number;
  offset?: number;
}

export function useReports(filters: ReportFilters = {}) {
  return useQuery({
    queryKey: ['reports', filters],
    queryFn: () => api.get<Paginated<ReportListItem>>(`/reports${qs({ ...filters })}`),
    refetchInterval: 20000,
  });
}

export function useReport(reportId?: string) {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => api.get<ReportDetail>(`/reports/${reportId}`),
    enabled: Boolean(reportId),
  });
}

export function useReviewQueue(site?: string, sort = 'oldest', limit = 50) {
  return useQuery({
    queryKey: ['review-queue', site, sort, limit],
    queryFn: () =>
      api.get<Paginated<ReportListItem>>(`/review-queue${qs({ site, sort, limit })}`),
    refetchInterval: 10000, // the queue is the thing people watch
  });
}

export function useReviewAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      action,
      correctedSif,
      correctedLsr,
      notes,
    }: {
      reportId: string;
      action: 'confirm' | 'correct' | 'reject';
      correctedSif?: boolean | null;
      correctedLsr?: string | null;
      notes?: string;
    }) =>
      api.post(`/review-queue/${reportId}/action`, {
        action,
        corrected_sif_potential: correctedSif ?? null,
        corrected_lsr_tag: correctedLsr ?? null,
        reviewer_notes: notes ?? '',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] });
      qc.invalidateQueries({ queryKey: ['summary'] });
      qc.invalidateQueries({ queryKey: ['reports'] });
      qc.invalidateQueries({ queryKey: ['audit'] });
    },
  });
}

/* -------------------------------------------------------------------------
 * Patterns
 * ---------------------------------------------------------------------- */

export function useAssociations(site?: string, topN = 20) {
  return useQuery({
    queryKey: ['associations', site, topN],
    queryFn: () => api.get<AssociationsResponse>(`/patterns/associations${qs({ site, top_n: topN })}`),
    staleTime: 120000,
  });
}

export function useBarrierFailures(site?: string, minCount = 5) {
  return useQuery({
    queryKey: ['barrier-failures', site, minCount],
    queryFn: () =>
      api.get<{ items: BarrierFailureRow[] }>(
        `/patterns/barrier-failures${qs({ site, min_count: minCount })}`,
      ),
    staleTime: 120000,
  });
}

/* -------------------------------------------------------------------------
 * Recommendations
 * ---------------------------------------------------------------------- */

export function useRecommendations() {
  return useQuery({
    queryKey: ['recommendations'],
    queryFn: () =>
      api.get<{ recommendations: RecommendationListItem[] }>('/recommendations'),
    staleTime: 60000,
  });
}

export function useRecommendation(patternId?: string) {
  return useQuery({
    queryKey: ['recommendation', patternId],
    queryFn: () => api.get<RecommendationDetail>(`/recommendations/${patternId}`),
    enabled: Boolean(patternId),
  });
}

/* -------------------------------------------------------------------------
 * Admin
 * ---------------------------------------------------------------------- */

export function useAuditLog(limit = 50) {
  return useQuery({
    queryKey: ['audit', limit],
    queryFn: () => api.get<Paginated<AuditEntry>>(`/audit-log${qs({ limit })}`),
    refetchInterval: 20000,
  });
}

export function useSites() {
  return useQuery({
    queryKey: ['sites'],
    queryFn: () => api.get<{ sites: { site_id: string; canonical_name: string }[] }>('/sites'),
    staleTime: Infinity,
  });
}

export function useRecomputePatterns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post('/admin/recompute-patterns', undefined, { timeoutMs: 120000 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clusters'] });
      qc.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}
