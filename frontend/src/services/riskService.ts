import { apiRequest } from '../api/client';
import {
  mockSummary,
  mockRankings,
  mockClusters,
  mockTrends,
  mockTrendAlerts,
} from '../data/mockData';
import type {
  DashboardSummary,
  RankingRow,
  PrecursorCluster,
  TrendPoint,
  TrendAlert,
} from '../types/sentinel';

export const riskService = {
  async getDashboardSummary(): Promise<{ summary: DashboardSummary; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<DashboardSummary>('/dashboard/summary');
    if (!isFallback && data) {
      return { summary: data, isFallback: false };
    }
    return { summary: mockSummary, isFallback: true };
  },

  async getRankings(metric: 'simple' | 'composite' = 'simple', siteFilter?: string): Promise<{ rankings: RankingRow[]; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ rankings: RankingRow[] }>(
      `/dashboard/rankings?metric=${metric}`
    );
    if (!isFallback && data) {
      let filtered = data.rankings;
      if (siteFilter && siteFilter !== 'All Sites') {
        filtered = filtered.filter((r) => r.group.toLowerCase() === siteFilter.toLowerCase());
      }
      return { rankings: filtered, isFallback: false };
    }

    let filtered = [...mockRankings];
    if (siteFilter && siteFilter !== 'All Sites') {
      filtered = filtered.filter((r) => r.group.toLowerCase() === siteFilter.toLowerCase());
    }

    return { rankings: filtered, isFallback: true };
  },

  async getClusters(siteFilter?: string): Promise<{ clusters: PrecursorCluster[]; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ clusters: PrecursorCluster[] }>(
      `/dashboard/clusters${siteFilter ? `?site=${siteFilter}` : ''}`
    );
    if (!isFallback && data) {
      return { clusters: data.clusters, isFallback: false };
    }
    let filtered = [...mockClusters];
    if (siteFilter && siteFilter !== 'All Sites') {
      filtered = filtered.filter((c) => c.sites.some((s) => s.toLowerCase() === siteFilter.toLowerCase()));
    }
    return { clusters: filtered, isFallback: true };
  },

  async getTrends(siteFilter?: string): Promise<{ series: TrendPoint[]; alerts: TrendAlert[]; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ series: TrendPoint[]; alerts: TrendAlert[] }>(
      `/dashboard/trends${siteFilter ? `?site=${siteFilter}` : ''}`
    );
    if (!isFallback && data) {
      return { series: data.series, alerts: data.alerts, isFallback: false };
    }
    return { series: mockTrends, alerts: mockTrendAlerts, isFallback: true };
  },
};
