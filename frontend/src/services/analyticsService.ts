import { mockLifeSavingRules, mockTrends, mockRankings } from '../data/mockData';
import type { LifeSavingRule, TrendPoint, RankingRow } from '../types/sentinel';

export const analyticsService = {
  async getLifeSavingRules(): Promise<{ rules: LifeSavingRule[]; isFallback: boolean }> {
    return { rules: mockLifeSavingRules, isFallback: true };
  },

  async getAnalyticsData(): Promise<{
    trends: TrendPoint[];
    sites: RankingRow[];
    rules: LifeSavingRule[];
    isFallback: boolean;
  }> {
    return {
      trends: mockTrends,
      sites: mockRankings,
      rules: mockLifeSavingRules,
      isFallback: true,
    };
  },
};
