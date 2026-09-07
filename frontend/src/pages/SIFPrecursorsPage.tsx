import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDown, Sparkles, ArrowRight } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { mockClusters } from '../data/mockData';

export const SIFPrecursorsPage: React.FC = () => {
  const navigate = useNavigate();

  const funnelSteps = [
    {
      stage: 'Total Safety Observations',
      count: '12,482',
      pct: '100%',
      desc: 'All field safety reports, near-misses, and UA/UC logs ingested',
      color: 'bg-slate-800 border-slate-700 text-slate-300',
    },
    {
      stage: 'Unsafe Conditions & Hazards',
      count: '3,420',
      pct: '27.4%',
      desc: 'Filtered physical equipment and operational condition hazards',
      color: 'bg-blue-950/60 border-blue-800/80 text-blue-300',
    },
    {
      stage: 'High-Risk Events',
      count: '512',
      pct: '4.1%',
      desc: 'High-energy hazards with active personnel exposure',
      color: 'bg-yellow-950/60 border-yellow-800/80 text-yellow-300',
    },
    {
      stage: 'SIF Precursors Detected',
      count: '64',
      pct: '0.51%',
      desc: 'High-confidence precursor events capable of causing fatality or permanent disability',
      color: 'bg-amber-950/80 border-amber-600/80 text-amber-200',
    },
    {
      stage: 'Critical Escalation Risk',
      count: '14',
      pct: '0.11%',
      desc: 'Immediate emergency intervention required across critical barrier failures',
      color: 'bg-red-950/90 border-red-600 text-red-100 font-bold shadow-lg shadow-red-500/10',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
            Serious Injury & Fatality (SIF) Precursors
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Automated detection and classification of low-frequency, high-consequence safety precursor events.
          </p>
        </div>

        {/* Hero Statistic */}
        <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 px-5 py-2.5 rounded-xl shadow-lg font-telemetry">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase">ACTIVE SIF PRECURSORS</div>
            <div className="text-2xl font-black text-amber-400">64</div>
          </div>
          <div className="h-8 w-px bg-slate-800" />
          <div>
            <div className="text-[10px] font-bold text-red-400 uppercase">CRITICAL ESCALATIONS</div>
            <div className="text-2xl font-black text-red-400">14</div>
          </div>
        </div>
      </div>

      {/* SIF RISK FUNNEL VISUALIZATION */}
      <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry">
                Sentinel SIF Precursor Detection Funnel
              </h3>
              <p className="text-xs text-slate-400">
                How Sentinel isolates critical SIF precursors out of thousands of routine reports
              </p>
            </div>
          </div>
          <span className="text-xs font-telemetry text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 font-bold">
            0.51% SIF Conversion Rate
          </span>
        </div>

        {/* Funnel Rows */}
        <div className="space-y-2 py-2 max-w-4xl mx-auto">
          {funnelSteps.map((step, idx) => (
            <React.Fragment key={step.stage}>
              <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${step.color}`}>
                <div className="space-y-0.5">
                  <div className="text-xs font-bold font-telemetry uppercase tracking-wider">
                    STAGE 0{idx + 1} — {step.stage}
                  </div>
                  <div className="text-xs opacity-80">{step.desc}</div>
                </div>

                <div className="text-right font-telemetry shrink-0 ml-4">
                  <div className="text-xl font-black">{step.count}</div>
                  <div className="text-[10px] opacity-75">{step.pct} of total</div>
                </div>
              </div>

              {idx < funnelSteps.length - 1 && (
                <div className="flex justify-center my-0.5">
                  <ArrowDown className="w-4 h-4 text-slate-600" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* SIF PRECURSOR CATEGORY CARDS */}
      <div className="space-y-4">
        <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry">
          Active SIF Precursor Cluster Categories
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockClusters.map((cluster) => (
            <div
              key={cluster.cluster_id}
              className="rounded-lg bg-slate-900 border border-slate-800 p-5 space-y-3 hover:border-amber-500/40 transition-all shadow-lg"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold font-telemetry text-amber-400 bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/30">
                    #{cluster.cluster_id}
                  </span>
                  <span className="text-xs font-bold text-slate-200">
                    {cluster.primary_lsr}
                  </span>
                </div>
                <RiskBadge level={cluster.risk_level} size="sm" />
              </div>

              <h4 className="text-sm font-extrabold text-slate-100">
                {cluster.pattern_summary}
              </h4>

              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded border border-slate-800">
                {cluster.why_it_matters}
              </p>

              <div className="grid grid-cols-3 gap-2 text-xs font-telemetry pt-1">
                <div>
                  <span className="text-slate-500 block text-[10px]">OCCURRENCES</span>
                  <span className="font-bold text-slate-100 text-base">{cluster.member_count}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">GROWTH VELOCITY</span>
                  <span className="font-bold text-red-400 text-base">+{cluster.growth_rate}%</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">AFFECTED SITES</span>
                  <span className="font-bold text-blue-400 text-base">{cluster.sites.length} sites</span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => navigate('/patterns')}
                  className="px-3 py-1.5 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-bold transition-all flex items-center gap-1.5"
                >
                  Inspect Cluster Evidence <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
