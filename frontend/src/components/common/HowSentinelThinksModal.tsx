import React from 'react';
import { X, Brain, ShieldAlert, Cpu, CheckCircle } from 'lucide-react';

interface HowSentinelThinksModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HowSentinelThinksModal: React.FC<HowSentinelThinksModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-900/95 z-10">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
              <Brain className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100 font-telemetry uppercase tracking-wider">
                How Sentinel Thinks — Methodology & Architecture
              </h2>
              <p className="text-xs text-slate-400">
                PS 26165 Technical Blueprint & SIF Precursor Intelligence Reasoning Model
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Traditional vs Sentinel Comparison */}
          <div className="bg-slate-950/80 rounded-xl p-5 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 font-telemetry uppercase tracking-wider flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Paradigm Shift: Outcome Severity vs. SIF Potential</span>
            </h3>

            {/* Comparison Visual */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Traditional */}
              <div className="p-4 rounded-lg bg-red-950/10 border border-red-500/20 space-y-2">
                <div className="text-xs font-bold text-red-400 uppercase tracking-wider font-telemetry">
                  Traditional HSE Reactive Thinking
                </div>
                <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono py-2">
                  <span>Report</span> &rarr; <span>Injury Severity</span> &rarr; <span>Priority</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Focuses on actual injury outcomes. Ignores high-energy near-misses where luck prevented a fatality.
                </p>
              </div>

              {/* Sentinel */}
              <div className="p-4 rounded-lg bg-emerald-950/10 border border-emerald-500/30 space-y-2">
                <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider font-telemetry">
                  Sentinel Precursor Intelligence
                </div>
                <div className="text-xs text-emerald-300 font-mono py-1 flex flex-wrap items-center gap-1">
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">Activity</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">Energy</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">Barrier</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">Exposure</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">SIF</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">LSR</span> &rarr;
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">Pattern</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Evaluates energy exposure & safety barrier state independent of actual outcome.
                </p>
              </div>
            </div>
          </div>

          {/* 3-Way Barrier State Explanation */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center space-x-2 text-emerald-400 font-telemetry text-xs font-bold uppercase">
                <CheckCircle className="w-4 h-4" />
                <span>Confirmed Effective</span>
              </div>
              <p className="text-xs text-slate-400">
                Explicit textual evidence confirms barrier was installed, verified, and operational.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center space-x-2 text-amber-400 font-telemetry text-xs font-bold uppercase">
                <ShieldAlert className="w-4 h-4" />
                <span>Uncertain / Degraded</span>
              </div>
              <p className="text-xs text-slate-400">
                Barrier was present but compromised, expired, improperly used, or partially bypassed.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center space-x-2 text-slate-400 font-telemetry text-xs font-bold uppercase">
                <X className="w-4 h-4 text-red-400" />
                <span>Absent / Not Confirmed</span>
              </div>
              <p className="text-xs text-slate-400">
                Barrier was missing or unmentioned. Absence of evidence is not treated as evidence of safety.
              </p>
            </div>
          </div>

          {/* Industry Framework Grounding & Governance */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
            <h4 className="text-xs font-bold text-slate-300 font-telemetry uppercase tracking-wider flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Safety Intelligence Framework & Governance</span>
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-400">
              <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                <strong className="text-slate-200 block mb-1">DEKRA SIF Principles</strong>
                Focus on high-energy exposure & critical barrier failures.
              </div>
              <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                <strong className="text-slate-200 block mb-1">EEI SCL Reasoning</strong>
                Energy-based hazard identification and safety controls.
              </div>
              <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                <strong className="text-slate-200 block mb-1">IOGP Life-Saving Rules</strong>
                Standardized mapping to 9 global upstream safety rules.
              </div>
              <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                <strong className="text-slate-200 block mb-1">Human-in-the-Loop</strong>
                HSE analyst review queue & auditable model retraining.
              </div>
            </div>
            <p className="text-[11px] text-slate-500 italic mt-2">
              Disclaimer: Sentinel's prototype methodology is informed by established industry frameworks and designed for enterprise integration with OIL HSSE systems.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-end bg-slate-900/95">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-telemetry text-xs font-bold transition-colors"
          >
            Close Methodology Brief
          </button>
        </div>
      </div>
    </div>
  );
};
