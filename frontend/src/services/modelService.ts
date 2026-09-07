import { apiRequest } from '../api/client';
import { mockModelPerformance } from '../data/mockData';
import type { ModelPerformanceData } from '../types/sentinel';

export const modelService = {
  async getModelPerformance(): Promise<{ performance: ModelPerformanceData; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ status: string; model_version: string }>('/health');
    if (!isFallback && data) {
      return {
        performance: {
          ...mockModelPerformance,
          model_version: data.model_version || mockModelPerformance.model_version,
        },
        isFallback: false,
      };
    }
    return { performance: mockModelPerformance, isFallback: true };
  },
};
