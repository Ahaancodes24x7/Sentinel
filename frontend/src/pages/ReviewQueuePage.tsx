import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Eye } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { mockReports } from '../data/mockData';
import { reportsService } from '../services/reportsService';
import type { ReportItem, Bucket } from '../types/sentinel';

export const ReviewQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialBucket = (searchParams.get('bucket') as Bucket) || 'LOW_CONF_REVIEW';

  const [activeBucket, setActiveBucket] = useState<Bucket | 'ALL'>(initialBucket);
  const [queue, setQueue] = useState<ReportItem[]>(mockReports);
  const [notes, setNotes] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    const b = searchParams.get('bucket') as Bucket;
    if (b) setActiveBucket(b);
  }, [searchParams]);

  const filteredQueue = queue.filter((r) => {
    if (activeBucket === 'ALL') return true;
    return r.bucket === activeBucket;
  });

  const handleAction = async (reportId: string, action: 'confirm' | 'correct' | 'reject' | 'info') => {
    const note = notes[reportId] || '';
    await reportsService.submitReviewAction(reportId, action, note);
    setQueue((prev) => prev.filter((r) => r.report_id !== reportId));
    alert(`Report ${reportId} action [${action.toUpperCase()}] recorded and added to retraining queue!`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Eye className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              HSE Review Queue — 4-Bucket Triage
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Human-in-the-Loop review for auto-routed high SIF precursors, low-confidence predictions, and missing field reports.
          </p>
        </div>

        <span className="text-xs font-telemetry font-bold text-purple-300 bg-purple-500/10 px-3 py-1.5 rounded-lg border border-purple-500/20 self-start sm:self-auto">
          2-Reviewer Agreement Active
        </span>
      </div>

      {/* 4-BUCKET TABS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-telemetry">
        <button
          onClick={() => setActiveBucket('HIGH_CONF_SIF')}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${activeBucket === 'HIGH_CONF_SIF'
              ? 'bg-red-950/40 border-red-500 ring-2 ring-red-500/30'
              : 'bg-slate-900 border-slate-800 hover:border-slate-700'
            }`}
        >
          <div className="text-[10px] font-bold text-red-400 uppercase">1. HIGH-CONF SIF</div>
          <div className="text-xl font-black text-slate-100 mt-0.5">48 Items</div>
          <div className="text-[10px] text-slate-400">Auto-routed for priority review</div>
        </button>

        <button
          onClick={() => setActiveBucket('LOW_CONF_REVIEW')}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${activeBucket === 'LOW_CONF_REVIEW'
              ? 'bg-amber-950/40 border-amber-500 ring-2 ring-amber-500/30'
              : 'bg-slate-900 border-slate-800 hover:border-slate-700'
            }`}
        >
          <div className="text-[10px] font-bold text-amber-400 uppercase">2. AMBIGUOUS / LOW-CONF</div>
          <div className="text-xl font-black text-slate-100 mt-0.5">16 Items</div>
          <div className="text-[10px] text-slate-400">Requires human verification</div>
        </button>

        <button
          onClick={() => setActiveBucket('NON_SIF')}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${activeBucket === 'NON_SIF'
              ? 'bg-emerald-950/40 border-emerald-500 ring-2 ring-emerald-500/30'
              : 'bg-slate-900 border-slate-800 hover:border-slate-700'
            }`}
        >
          <div className="text-[10px] font-bold text-emerald-400 uppercase">3. HIGH-CONF NON-SIF</div>
          <div className="text-xl font-black text-slate-100 mt-0.5">8,914 Items</div>
          <div className="text-[10px] text-slate-400">Sampled QA audit</div>
        </button>

        <button
          onClick={() => setActiveBucket('NEEDS_MORE_INFO')}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${activeBucket === 'NEEDS_MORE_INFO'
              ? 'bg-slate-800 border-slate-400 ring-2 ring-slate-400/30'
              : 'bg-slate-900 border-slate-800 hover:border-slate-700'
            }`}
        >
          <div className="text-[10px] font-bold text-slate-300 uppercase">4. INSUFFICIENT DETAIL</div>
          <div className="text-xl font-black text-slate-100 mt-0.5">127 Items</div>
          <div className="text-[10px] text-slate-400">Missing barrier/location data</div>
        </button>
      </div>

      {/* Queue Items List */}
      <div className="space-y-4">
        {filteredQueue.length > 0 ? (
          filteredQueue.map((item) => (
            <div
              key={item.report_id}
              className="rounded-xl bg-slate-900/90 border border-slate-800 p-5 space-y-4 shadow-xl hover:border-slate-700 transition-all"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => navigate(`/reports/${item.report_id}`)}
                    className="font-telemetry font-bold text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 px-2.5 py-1 rounded border border-blue-500/20"
                  >
                    {item.report_id}
                  </button>
                  <span className="text-xs font-bold text-slate-200">{item.site}</span>
                  <RiskBadge level={item.risk_level} size="sm" />
                </div>
                <span className="text-xs font-telemetry text-amber-400 font-bold">
                  Confidence: {Math.round((item.classification?.confidence || 0.85) * 100)}%
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed">
                {item.report_text}
              </div>

              <div className="p-3 rounded-lg bg-blue-950/30 border border-blue-900/40 text-xs text-blue-300 font-telemetry">
                <strong>AI Justification:</strong> {item.classification?.justification || 'Flagged due to unverified barrier control.'}
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <input
                  type="text"
                  placeholder="Enter review reason / technical notes..."
                  value={notes[item.report_id] || ''}
                  onChange={(e) => setNotes({ ...notes, [item.report_id]: e.target.value })}
                  className="flex-1 w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none font-mono"
                />
                <div className="flex items-center gap-2 w-full sm:w-auto font-telemetry">
                  <button
                    onClick={() => handleAction(item.report_id, 'confirm')}
                    className="flex-1 sm:flex-none px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md"
                  >
                    Confirm SIF
                  </button>
                  <button
                    onClick={() => handleAction(item.report_id, 'correct')}
                    className="flex-1 sm:flex-none px-3.5 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-md"
                  >
                    Correct
                  </button>
                  <button
                    onClick={() => handleAction(item.report_id, 'reject')}
                    className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold border border-slate-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-8 text-center bg-slate-900/60 rounded-xl border border-slate-800 text-slate-400 font-telemetry">
            No pending items in the selected queue bucket ({activeBucket}). All observations reviewed!
          </div>
        )}
      </div>
    </div>
  );
};
