import { apiRequest } from '../api/client';
import { mockReports } from '../data/mockData';
import type { ReportItem } from '../types/sentinel';

export interface ReportsFilter {
  site?: string;
  sif_potential?: boolean;
  bucket?: string;
  lsr_tag?: string;
  risk_level?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const reportsService = {
  async getReports(filters: ReportsFilter = {}): Promise<{ items: ReportItem[]; total: number; isFallback: boolean }> {
    const query = new URLSearchParams();
    if (filters.site && filters.site !== 'All Sites') query.append('site', filters.site);
    if (filters.sif_potential !== undefined) query.append('sif_potential', String(filters.sif_potential));
    if (filters.bucket) query.append('bucket', filters.bucket);
    if (filters.lsr_tag) query.append('lsr_tag', filters.lsr_tag);
    if (filters.limit) query.append('limit', String(filters.limit));
    if (filters.offset) query.append('offset', String(filters.offset));

    const { data, isFallback } = await apiRequest<{ items: ReportItem[]; total: number }>(`/reports?${query.toString()}`);

    if (!isFallback && data) {
      return { items: data.items, total: data.total, isFallback: false };
    }

    // Fallback filtering over mock dataset
    let filtered = [...mockReports];

    if (filters.site && filters.site !== 'All Sites') {
      filtered = filtered.filter((r) => r.site.toLowerCase() === filters.site?.toLowerCase());
    }
    if (filters.sif_potential !== undefined) {
      filtered = filtered.filter((r) => r.sif_potential === filters.sif_potential);
    }
    if (filters.bucket) {
      filtered = filtered.filter((r) => r.bucket === filters.bucket);
    }
    if (filters.lsr_tag) {
      filtered = filtered.filter((r) => r.lsr_tag.toLowerCase().includes(filters.lsr_tag!.toLowerCase()));
    }
    if (filters.risk_level) {
      filtered = filtered.filter((r) => r.risk_level === filters.risk_level);
    }
    if (filters.search) {
      const q = filters.search.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.report_id.toLowerCase().includes(q) ||
          r.site.toLowerCase().includes(q) ||
          r.report_text.toLowerCase().includes(q) ||
          r.hazard.toLowerCase().includes(q) ||
          r.failed_barrier.toLowerCase().includes(q)
      );
    }

    return {
      items: filtered,
      total: filtered.length,
      isFallback: true,
    };
  },

  async getReportById(id: string): Promise<{ report: ReportItem | null; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<ReportItem>(`/reports/${id}`);
    if (!isFallback && data) {
      return { report: data, isFallback: false };
    }

    const found = mockReports.find((r) => r.report_id === id) || mockReports[0];
    return { report: found, isFallback: true };
  },

  async ingestReports(csvOrJson: FormData | object): Promise<{ ingested_count: number; batch_id: string }> {
    const options: RequestInit = { method: 'POST' };
    if (csvOrJson instanceof FormData) {
      options.body = csvOrJson;
      // Do not set Content-Type header so fetch handles boundary
      delete (options as any).headers;
    } else {
      options.body = JSON.stringify(csvOrJson);
    }

    const { data, isFallback } = await apiRequest<{ ingested_count: number; batch_id: string }>(
      '/reports/ingest',
      options
    );

    if (!isFallback && data) {
      return data;
    }

    return {
      ingested_count: 1,
      batch_id: `batch_${Math.random().toString(36).substring(2, 8)}`,
    };
  },

  async submitReviewAction(
    reportId: string,
    action: 'confirm' | 'correct' | 'reject' | 'info',
    reviewerNotes: string,
    correctedLsrTag?: string
  ) {
    const { data, isFallback } = await apiRequest<{ report_id: string; review_action_id: string; status: string }>(
      `/review-queue/${reportId}/action`,
      {
        method: 'POST',
        body: JSON.stringify({
          action,
          reviewer_notes: reviewerNotes,
          corrected_lsr_tag: correctedLsrTag,
        }),
      }
    );

    if (!isFallback && data) return data;

    return {
      report_id: reportId,
      review_action_id: `rv_${Math.floor(Math.random() * 9000) + 1000}`,
      status: 'recorded',
      promoted_to_training_queue: action === 'correct' || action === 'confirm',
    };
  },
};
