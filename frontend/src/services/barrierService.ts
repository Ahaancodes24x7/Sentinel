import { mockBarriers } from '../data/mockData';
import type { BarrierStat } from '../types/sentinel';

export const barrierService = {
  async getBarriers(siteFilter?: string): Promise<{ barriers: BarrierStat[]; totalFailures: number; isFallback: boolean }> {
    let filtered = [...mockBarriers];
    if (siteFilter && siteFilter !== 'All Sites') {
      // simulate site variance
      filtered = filtered.map((b) => ({
        ...b,
        failures: Math.round(b.failures * 0.4),
      }));
    }
    const totalFailures = filtered.reduce((acc, curr) => acc + curr.failures, 0);
    return { barriers: filtered, totalFailures, isFallback: true };
  },
};
