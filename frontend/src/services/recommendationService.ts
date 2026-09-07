import { apiRequest } from '../api/client';
import { mockRecommendations, mockActionPlans } from '../data/mockData';
import type { Recommendation, ActionPlan } from '../types/sentinel';

export const recommendationService = {
  async getRecommendations(): Promise<{ recommendations: Recommendation[]; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ recommendations: Recommendation[] }>('/recommendations');
    if (!isFallback && data) {
      return { recommendations: data.recommendations, isFallback: false };
    }
    return { recommendations: mockRecommendations, isFallback: true };
  },

  async getRecommendationByPatternId(patternId: string): Promise<{ recommendation: Recommendation | null; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<Recommendation>(`/recommendations/${patternId}`);
    if (!isFallback && data) {
      return { recommendation: data, isFallback: false };
    }
    const found = mockRecommendations.find((r) => r.pattern_id === patternId) || mockRecommendations[0];
    return { recommendation: found, isFallback: true };
  },

  async createActionPlan(
    patternId: string,
    selectedRanks: number[],
    targetSites: string[],
    plannedStartDate: string
  ): Promise<{ action_plan_id: string; pattern_id: string; status: string }> {
    const { data, isFallback } = await apiRequest<{ action_plan_id: string; pattern_id: string; status: string }>(
      `/recommendations/${patternId}/action-plan`,
      {
        method: 'POST',
        body: JSON.stringify({
          selected_intervention_ranks: selectedRanks,
          target_sites: targetSites,
          planned_start_date: plannedStartDate,
        }),
      }
    );

    if (!isFallback && data) return data;

    const newPlan: ActionPlan = {
      action_plan_id: `ap_${Math.floor(Math.random() * 9000) + 1000}`,
      pattern_id: patternId,
      selected_interventions: selectedRanks,
      target_sites: targetSites,
      planned_start_date: plannedStartDate,
      status: 'planned',
      created_by: 'HSE Manager',
      created_at: new Date().toISOString(),
    };
    mockActionPlans.unshift(newPlan);

    return {
      action_plan_id: newPlan.action_plan_id,
      pattern_id: patternId,
      status: 'planned',
    };
  },
};
