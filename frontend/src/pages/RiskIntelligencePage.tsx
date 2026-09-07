import React, { useState } from 'react';
import { Info, BarChart3, Building2 } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { mockRankingRows } from '../data/mockData';
import type { RankingRow } from '../types/sentinel';

export const RiskIntelligencePage: React.FC = () => {
  const [metricMode, setMetricMode] = useState<'ratio' | 'composite'>('ratio');
  const [rankingDimension, setRankingDimension] = useState<'site' | 'activity' | 'barrier'>('site');
  const [showCultureTooltip, setShowCultureTooltip] = useState(false);

  const activityRankings: RankingRow[] = [
    {
      group: 'Crane Lifting Operations',
      sif_flagged_count: 42,
      total_reports: 420,
      density: 10.0,
      trend_direction: 'up',
      trend_pct: 31.0,
      primary_lsr: 'Line of Fire',
      risk_score: 92.0,
      barrier_failures: 27,
      risk_level: 'CRITICAL',
      psif_rate: 10.0,
    },
    {
      group: 'Working at Elevation (>4m)',
      sif_flagged_count: 34,
      total_reports: 510,
      density: 6.66,
      trend_direction: 'up',
      trend_pct: 18.2,
      primary_lsr: 'Working at Height',
      risk_score: 88.5,
      barrier_failures: 34,
      risk_level: 'CRITICAL',
      psif_rate: 6.66,
    },
    {
      group: 'Hydrocarbon Line Breaking',
      sif_flagged_count: 19,
      total_reports: 320,
      density: 5.93,
      trend_direction: 'up',
      trend_pct: 42.5,
      primary_lsr: 'Energy Isolation',
      risk_score: 84.1,
      barrier_failures: 19,
      risk_level: 'CRITICAL',
      psif_rate: 5.93,
    },
  ];

  const barrierRankings: RankingRow[] = [
    {
      group: 'Fall Protection Lanyard',
      sif_flagged_count: 127,
      total_reports: 1240,
      density: 10.24,
      trend_direction: 'up',
      trend_pct: 42.0,
      primary_lsr: 'Working at Height',
      risk_score: 95.0,
      barrier_failures: 127,
      risk_level: 'CRITICAL',
      psif_rate: 10.24,
    },
    {
      group: 'LOTO Lock-Out Verification',
      sif_flagged_count: 91,
      total_reports: 1100,
      density: 8.27,
      trend_direction: 'up',
      trend_pct: 18.0,
      primary_lsr: 'Energy Isolation',
      risk_score: 89.2,
      barrier_failures: 91,
      risk_level: 'CRITICAL',
      psif_rate: 8.27,
    },
    {
      group: 'Exclusion Zone Barricading',
      sif_flagged_count: 63,
      total_reports: 950,
      density: 6.63,
      trend_direction: 'up',
      trend_pct: 8.0,
      primary_lsr: 'Line of Fire',
      risk_score: 81.4,
      barrier_failures: 63,
      risk_level: 'HIGH',
      psif_rate: 6.63,
    },
  ];

  const currentRankings =
    rankingDimension === 'site'
      ? mockRankingRows
      : rankingDimension === 'activity'
        ? activityRankings
        : barrierRankings;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              Precursor Density & Risk Intelligence
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Normalized SIF precursor rates, site density rankings, and barrier health metrics across facilities.
          </p>
        </div>

        {/* Culture Tooltip Notice */}
        <div className="relative">
          <div className="flex items-center space-x-1.5 text-xs font-telemetry text-amber-300 bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/20">
            <Info className="w-4 h-4 text-amber-400" />
            <span>Reporting Culture Warning</span>
            <button
              onMouseEnter={() => setShowCultureTooltip(true)}
              onMouseLeave={() => setShowCultureTooltip(false)}
              className="ml-1 font-bold text-amber-400 underline"
            >
              Why?
            </button>
          </div>

          {showCultureTooltip && (
            <div className="absolute right-0 top-10 w-80 p-3 bg-slate-900 border border-amber-500/40 rounded-xl shadow-2xl z-50 text-xs text-slate-300">
              <div className="font-bold text-amber-400 mb-1 font-telemetry">
                Important Reporting Culture Disclaimer
              </div>
              "Reporting volume is influenced by reporting culture. High reporting volume does NOT automatically imply higher risk. Use normalized rates and barrier health for comparison."
            </div>
          )}
        </div>
      </div>

      {/* METRIC TOGGLE & RANKING DIMENSION SELECTOR */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 font-telemetry">
        {/* Metric Toggle */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-slate-400 uppercase">Ranking Metric:</span>
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              onClick={() => setMetricMode('ratio')}
              className={`px-3 py-1 rounded font-bold transition-all ${metricMode === 'ratio'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Simple PSIF Ratio (%)
            </button>
            <button
              onClick={() => setMetricMode('composite')}
              className={`px-3 py-1 rounded font-bold transition-all ${metricMode === 'composite'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Composite Indicator (SME Tunable)
            </button>
          </div>
        </div>

        {/* Dimension Tabs */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-slate-400 uppercase">Group Dimension:</span>
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              onClick={() => setRankingDimension('site')}
              className={`px-3 py-1 rounded font-bold transition-all ${rankingDimension === 'site'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Site Ranking
            </button>
            <button
              onClick={() => setRankingDimension('activity')}
              className={`px-3 py-1 rounded font-bold transition-all ${rankingDimension === 'activity'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Activity Ranking
            </button>
            <button
              onClick={() => setRankingDimension('barrier')}
              className={`px-3 py-1 rounded font-bold transition-all ${rankingDimension === 'barrier'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Barrier Ranking
            </button>
          </div>
        </div>
      </div>

      {/* DENSITY RANKINGS TABLE */}
      <div className="rounded-xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-2xl">
        <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between font-telemetry">
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100">
            Precursor Density Scorecard — {rankingDimension.toUpperCase()} RANKINGS
          </h3>
          <span className="text-xs text-slate-400">
            Showing {currentRankings.length} groups
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300 font-telemetry">
            <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Group / Entity Name</th>
                <th className="px-4 py-3">Total Reports</th>
                <th className="px-4 py-3">SIF Potential Count</th>
                <th className="px-4 py-3">
                  {metricMode === 'ratio' ? 'PSIF Rate (%)' : 'Composite Indicator Score'}
                </th>
                <th className="px-4 py-3">Barrier Failures</th>
                <th className="px-4 py-3">30D Trend</th>
                <th className="px-4 py-3">Primary LSR</th>
                <th className="px-4 py-3">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {currentRankings.map((row) => (
                <tr key={row.group} className="hover:bg-slate-800/80 transition-colors">
                  <td className="px-4 py-3.5 font-bold text-slate-100 flex items-center space-x-2">
                    <Building2 className="w-4 h-4 text-blue-400 shrink-0" />
                    <span>{row.group}</span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-300 font-semibold">{row.total_reports.toLocaleString()}</td>
                  <td className="px-4 py-3.5 font-bold text-red-400">{row.sif_flagged_count}</td>
                  <td className="px-4 py-3.5 font-black text-sm text-amber-300">
                    {metricMode === 'ratio' ? `${row.psif_rate}%` : row.risk_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3.5 text-purple-300 font-bold">{row.barrier_failures}</td>
                  <td className={`px-4 py-3.5 font-bold ${row.trend_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {row.trend_pct > 0 ? `+${row.trend_pct}%` : `${row.trend_pct}%`}
                  </td>
                  <td className="px-4 py-3.5 text-slate-400">{row.primary_lsr}</td>
                  <td className="px-4 py-3.5"><RiskBadge level={row.risk_level} size="sm" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
