import React from 'react';
import { Download, CheckCircle, Sparkles, X, ShieldAlert, AlertTriangle } from 'lucide-react';

interface SafetyBriefModalProps {
  isOpen: boolean;
  onClose: () => void;
  siteFilter: string;
}

export const SafetyBriefModal: React.FC<SafetyBriefModalProps> = ({ isOpen, onClose, siteFilter }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-3xl overflow-hidden rounded-xl bg-slate-900 border border-slate-700 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 uppercase tracking-wide">
                Sentinel Executive Safety Brief
              </h3>
              <p className="text-xs text-slate-400">
                AI-Generated Executive Summary — Facility: <span className="text-blue-400 font-semibold">{siteFilter}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto font-sans">
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <span className="text-xs font-telemetry font-bold text-slate-400 uppercase">
                EXECUTIVE RISK ASSESSMENT — PERIOD ENDING SEP 08, 2026
              </span>
              <span className="text-xs font-telemetry text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                SENTINEL AI v0.3 CERTIFIED
              </span>
            </div>

            <div className="text-sm text-slate-200 leading-relaxed">
              <p className="font-semibold text-slate-100 mb-2">
                Key Findings & Escalation Warning:
              </p>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="flex items-start gap-2">
                  <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>1. SIF Precursor Spike:</strong> Sentinel AI detected a <strong>23% increase</strong> in high-risk precursor reports across primary operations, with <strong>64 active SIF precursors</strong> flagged.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>2. Primary Barrier Vulnerability:</strong> <strong>Fall Protection Verification</strong> represents the most frequently failed barrier (127 occurrences, +42% over 30 days).
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>3. Priority Recommended Action:</strong> Immediate targeted scaffolding & tie-off audit recommended for North Refinery & Processing Unit 4.
                  </span>
                </li>
              </ul>
            </div>
          </div>

          {/* Detailed Metric Grid */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Total Reports</div>
              <div className="text-xl font-bold font-telemetry text-slate-100 mt-1">12,482</div>
            </div>
            <div className="p-3 rounded bg-red-950/20 border border-red-900/40">
              <div className="text-[11px] font-semibold text-red-400 uppercase">Critical SIFs</div>
              <div className="text-xl font-bold font-telemetry text-red-400 mt-1">23</div>
            </div>
            <div className="p-3 rounded bg-amber-950/20 border border-amber-900/40">
              <div className="text-[11px] font-semibold text-amber-400 uppercase">Barrier Failures</div>
              <div className="text-xl font-bold font-telemetry text-amber-400 mt-1">312</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/90">
          <span className="text-xs text-slate-500 font-telemetry">
            Report ID: BRIEF-20260908-SR09
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              Close
            </button>
            <button
              onClick={() => {
                alert('Safety Brief PDF exported to downloads folder.');
                onClose();
              }}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg transition-all"
            >
              <Download className="w-4 h-4" />
              Download Brief PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
