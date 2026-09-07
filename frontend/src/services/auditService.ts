import { apiRequest } from '../api/client';
import { mockAuditLogs } from '../data/mockData';
import type { AuditLogEntry } from '../types/sentinel';

export const auditService = {
  async getAuditLogs(): Promise<{ items: AuditLogEntry[]; isFallback: boolean }> {
    const { data, isFallback } = await apiRequest<{ items: AuditLogEntry[] }>('/audit-log');
    if (!isFallback && data) {
      return { items: data.items, isFallback: false };
    }
    return { items: mockAuditLogs, isFallback: true };
  },
};
