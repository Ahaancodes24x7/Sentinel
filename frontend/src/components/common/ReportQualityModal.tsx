import React from 'react';
import { X, AlertCircle, FileQuestion, ArrowRight } from 'lucide-react';
import type { ReportQualityStats } from '../../types/sentinel';

interface ReportQualityModalProps {
  isOpen: boolean;
  onClose: () => void;
  stats?: ReportQualityStats;
  onViewInsufficientReports?: () => void;
}

const defaultStats: ReportQualityStats = {
  complete_count: 12355,
  incomplete_count: 127,
  missing_barrier_pct: 62,
  missing_activity_pct: 18,
  missing_location_pct: 11,
  missing_exposure_pct: 9,
};

export const ReportQualityModal: React.FC<ReportQualityModalProps> = ({
  isOpen,
  onClose,
  stats = defaultStats,
  onViewInsufficientReports,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <FileQuestion className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 font-telemetry uppercase tracking-wider">
                Safety Observation Quality & Completeness
              </h2>
              <p className="text-xs text-slate-400">
                Evaluating report clarity, missing safety barrier details & data quality signals
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400 font-telemetry text-xl font-bold">
                {stats.complete_count.toLocaleString()}
              </div>
              <div>
                <div className="text-xs font-bold text-slate-200 uppercase font-telemetry">
                  Fully Structured Reports
                </div>
                <div className="text-[11px] text-slate-400">
                  Contains activity, energy, barrier & outcome
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400 font-telemetry text-xl font-bold">
                {stats.incomplete_count}
              </div>
              <div>
                <div className="text-xs font-bold text-amber-300 uppercase font-telemetry">
                  Require Additional Detail
                </div>
                <div className="text-[11px] text-amber-200/80">
                  Routing to "Insufficient Detail" queue
                </div>
              </div>
            </div>
          </div>

          {/* Missing Fields Breakdown */}
          <div className="space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <h4 className="text-xs font-bold text-slate-300 uppercase font-telemetry tracking-wider">
              Most Frequent Missing Information Types
            </h4>

            <div className="space-y-2.5">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Safety Barrier State (Unclear / Unmentioned)</span>
                  <span className="text-amber-400 font-telemetry font-bold">{stats.missing_barrier_pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: `${stats.missing_barrier_pct}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Specific Activity / Equipment ID</span>
                  <span className="text-blue-400 font-telemetry font-bold">{stats.missing_activity_pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${stats.missing_activity_pct}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Exact Location / Deck Level</span>
                  <span className="text-purple-400 font-telemetry font-bold">{stats.missing_location_pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-purple-500 rounded-full" style={{ width: `${stats.missing_location_pct}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Exposure Duration / Proximity</span>
                  <span className="text-cyan-400 font-telemetry font-bold">{stats.missing_exposure_pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${stats.missing_exposure_pct}%` }} />
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p>
              <strong>Safety System Insight:</strong> "Insufficient Information" is itself a critical safety signal. Reports lacking barrier information often correlate with site reporting friction or unclear hazard procedures.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between bg-slate-900/95">
          <span className="text-[11px] font-telemetry text-slate-500">
            Bucket #4: Insufficient Detail Queue
          </span>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-telemetry text-xs font-semibold transition-colors"
            >
              Close
            </button>
            <button
              onClick={() => {
                onClose();
                if (onViewInsufficientReports) onViewInsufficientReports();
              }}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-telemetry text-xs font-bold transition-colors flex items-center space-x-1.5"
            >
              <span>View Insufficient Reports</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
