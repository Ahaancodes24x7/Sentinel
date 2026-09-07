import React, { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { ActionPlanModal } from '../components/common/ActionPlanModal';
import { mockRecommendations } from '../data/mockData';
import type { Recommendation } from '../types/sentinel';

export const RecommendationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'recommended' | 'assigned' | 'in_progress' | 'completed'>('recommended');
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [recommendations, setRecommendations] = useState(mockRecommendations);

  const filteredRecs = recommendations.filter((r) => r.status === activeTab);

  const handleAction = (patternId: string, newStatus: 'assigned' | 'in_progress' | 'completed') => {
    setRecommendations((prev) =>
      prev.map((r) => (r.pattern_id === patternId ? { ...r, status: newStatus } : r))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Lightbulb className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              AI Recommended Interventions
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Targeted safety actions recommended by Sentinel AI to mitigate high-priority precursor patterns.
          </p>
        </div>

        <span className="text-xs font-telemetry font-bold text-blue-400 bg-blue-500/10 px-3 py-1.5 rounded-lg border border-blue-500/20">
          Intervention Engine v1.2
        </span>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {(['recommended', 'assigned', 'in_progress', 'completed'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-xs font-bold font-telemetry uppercase transition-all ${activeTab === tab
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
          >
            {tab.replace('_', ' ')} (
            {recommendations.filter((r) => r.status === tab).length})
          </button>
        ))}
      </div>

      {/* Recommendation Cards List */}
      <div className="space-y-4">
        {filteredRecs.length > 0 ? (
          filteredRecs.map((rec) => (
            <div
              key={rec.pattern_id}
              className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 space-y-4 shadow-xl hover:border-slate-700 transition-all"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <RiskBadge level={rec.priority} size="sm" />
                  <span className="text-xs font-bold font-telemetry text-purple-300 bg-purple-500/10 px-2.5 py-0.5 rounded border border-purple-500/20">
                    Pattern #{rec.pattern_id}
                  </span>
                  <span className="text-xs font-telemetry text-slate-400">
                    Owner: <strong className="text-slate-200">{rec.owner}</strong>
                  </span>
                </div>
                <div className="text-xs font-telemetry text-emerald-400 font-bold bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                  Confidence: {rec.confidence}%
                </div>
              </div>

              <h3 className="text-base font-extrabold text-slate-100">
                {rec.title}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-sans">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-400 uppercase font-telemetry block text-[10px]">
                    Reason & Evidence Basis:
                  </span>
                  <p className="text-slate-200">{rec.reason}</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-400 uppercase font-telemetry block text-[10px]">
                    Expected Objective & Impact:
                  </span>
                  <p className="text-slate-200">{rec.impact}</p>
                </div>
              </div>

              {/* Recommended Interventions Checklist */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-400 uppercase font-telemetry">
                  Prioritized Action Items:
                </span>
                <div className="space-y-1.5 text-xs font-sans">
                  {rec.recommended_interventions.map((item) => (
                    <div
                      key={item.rank}
                      className="p-2.5 rounded bg-slate-950/80 border border-slate-800/80 flex items-center justify-between"
                    >
                      <span className="text-slate-200">
                        <strong className="font-telemetry text-purple-300 mr-2">
                          #{item.rank} [{item.control_level.toUpperCase()}]
                        </strong>
                        {item.action}
                      </span>
                      <RiskBadge level={item.priority} size="sm" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <span className="text-xs text-slate-500 font-telemetry">
                  Target Sites: {rec.target_sites.join(', ')}
                </span>

                <div className="flex items-center gap-2 font-telemetry">
                  {rec.status === 'recommended' && (
                    <>
                      <button
                        onClick={() => handleAction(rec.pattern_id, 'assigned')}
                        className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md transition-all"
                      >
                        Assign to HSE Team
                      </button>
                      <button
                        onClick={() => {
                          setSelectedRec(rec);
                          setModalOpen(true);
                        }}
                        className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-md transition-all"
                      >
                        Approve & Deploy Action Plan
                      </button>
                    </>
                  )}
                  {rec.status === 'assigned' && (
                    <button
                      onClick={() => handleAction(rec.pattern_id, 'in_progress')}
                      className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs"
                    >
                      Start Implementation
                    </button>
                  )}
                  {rec.status === 'in_progress' && (
                    <button
                      onClick={() => handleAction(rec.pattern_id, 'completed')}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
                    >
                      Mark Completed
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-8 rounded-lg bg-slate-900 border border-slate-800 text-center text-slate-500 font-telemetry">
            No interventions currently in <strong className="text-slate-300">{activeTab}</strong> status.
          </div>
        )}
      </div>

      <ActionPlanModal
        recommendation={selectedRec}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => {
          if (selectedRec) handleAction(selectedRec.pattern_id, 'in_progress');
        }}
      />
    </div>
  );
};
