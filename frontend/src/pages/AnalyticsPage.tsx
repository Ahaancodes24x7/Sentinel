import React, { useState } from 'react';
import { Download, FileSpreadsheet, ShieldAlert, Info } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { mockTrends, mockEarlyWarningSignals } from '../data/mockData';

export const AnalyticsPage: React.FC = () => {
  const [granularity, setGranularity] = useState<'Daily' | 'Weekly' | 'Monthly' | 'Quarterly'>('Weekly');

  const handleExportCSV = () => {
    alert('Exporting safety analytics dataset to CSV file...');
  };

  const handleExportPDF = () => {
    alert('Generating comprehensive HSE Executive Analytics PDF Report...');
  };

  const ewSignal = mockEarlyWarningSignals[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
            Early Warning System & Safety Analytics
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Statistical process control (EWMA / CUSUM) baseline anomaly detection and multi-dimensional safety trend analytics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Granularity selector */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            {(['Daily', 'Weekly', 'Monthly', 'Quarterly'] as const).map((g) => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-3 py-1 rounded font-telemetry font-bold transition-all ${granularity === g ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
              >
                {g}
              </button>
            ))}
          </div>

          <button
            onClick={handleExportCSV}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 font-telemetry transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            Export CSV
          </button>

          <button
            onClick={handleExportPDF}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg font-telemetry transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Export PDF
          </button>
        </div>
      </div>

      {/* 1. EARLY WARNING SYSTEM HERO PANEL (CUSUM / EWMA) */}
      <div className="bg-slate-900/90 border border-amber-500/30 rounded-xl p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <ShieldAlert className="w-4 h-4" />
            </span>
            <div>
              <h3 className="text-sm font-extrabold text-slate-100 uppercase tracking-wider font-telemetry">
                Early Warning Baseline Anomaly System
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                CUSUM statistical baseline alerting — detecting unusual spikes in barrier degradation before actual incidents occur.
              </p>
            </div>
          </div>
          <span className="text-[11px] font-telemetry font-bold text-amber-300 bg-amber-500/10 px-3 py-1 rounded border border-amber-500/30">
            EWMA / CUSUM Engine Active
          </span>
        </div>

        {/* Signal breakdown card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 font-telemetry">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-amber-400 uppercase">Status Signal</span>
              <span className="px-2.5 py-0.5 rounded text-xs font-black bg-red-500/10 text-red-400 border border-red-500/30">
                UNUSUAL INCREASE
              </span>
            </div>

            <div className="space-y-1">
              <div className="text-xs text-slate-400">Target Barrier & Asset:</div>
              <div className="text-sm font-extrabold text-slate-100">{ewSignal.barrier}</div>
              <div className="text-xs text-blue-400 font-bold">{ewSignal.site}</div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
              <div className="bg-slate-900 p-2 rounded">
                <span className="text-slate-500 block text-[10px]">HISTORICAL BASELINE</span>
                <span className="font-bold text-slate-200">{ewSignal.baseline_rate} / week</span>
              </div>
              <div className="bg-slate-900 p-2 rounded">
                <span className="text-slate-500 block text-[10px]">CURRENT OBSERVED</span>
                <span className="font-extrabold text-red-400">{ewSignal.current_rate} / week</span>
              </div>
            </div>

            <div className="p-2.5 rounded bg-red-950/20 border border-red-900/40 text-xs text-red-200 space-y-1">
              <div className="font-bold text-red-400 uppercase">Recommended HSE Intervention</div>
              <p className="text-[11px] leading-snug">{ewSignal.recommendation}</p>
            </div>
          </div>

          {/* EWMA Baseline Chart (2 cols) */}
          <div className="lg:col-span-2 p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
            <div className="flex justify-between items-center text-xs font-telemetry mb-2">
              <span className="text-slate-300 font-bold uppercase">Weekly Barrier Failure Rate vs. Baseline</span>
              <span className="text-red-400 font-bold">+131% Baseline Exceedance</span>
            </div>

            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ewSignal.historical_data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="rounded bg-slate-900 border border-slate-700 p-2 text-xs font-telemetry">
                            <div className="font-bold text-slate-200">{label}</div>
                            <div className="text-slate-400">Baseline Rate: {payload[0].value}</div>
                            <div className="text-red-400 font-bold">Actual Observed: {payload[1].value}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                  <Line type="monotone" dataKey="baseline" stroke="#64748b" strokeDasharray="5 5" name="Historical CUSUM Baseline" strokeWidth={2} />
                  <Line type="monotone" dataKey="actual" stroke="#ef4444" name="Observed Barrier Failures" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Disclaimer */}
            <div className="text-[11px] text-slate-400 italic pt-1 border-t border-slate-800 flex items-center space-x-1.5">
              <Info className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>
                "This is an early-warning signal for unusual reporting activity, not a prediction of a future fatality."
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* MULTI-DIMENSIONAL TRENDS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-5 shadow-2xl space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry">
              Total Reports vs SIF Precursor Rate ({granularity})
            </h3>
            <p className="text-xs text-slate-400">Multi-period trend analysis</p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                <XAxis dataKey="period" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total" fill="#3b82f6" opacity={0.6} name="Total Reports" />
                <Bar dataKey="sif_count" fill="#ef4444" name="SIF Precursors" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-5 shadow-2xl space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry">
              High Risk Precursor Distribution
            </h3>
            <p className="text-xs text-slate-400">Breakdown by Life-Saving Rule category</p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={[
                  { category: 'Working at Height', count: 127 },
                  { category: 'Energy Isolation', count: 91 },
                  { category: 'Permit Verification', count: 74 },
                  { category: 'Line of Fire', count: 63 },
                  { category: 'Confined Space', count: 34 },
                  { category: 'Hot Work', count: 28 },
                ]}
                margin={{ top: 10, right: 20, left: 40, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" horizontal={false} />
                <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis dataKey="category" type="category" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} name="Precursor Counts" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
