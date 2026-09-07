import React, { useState } from 'react';
import type { Recommendation } from '../../types/sentinel';
import { recommendationService } from '../../services/recommendationService';
import { Check, X, ShieldCheck, Calendar, MapPin } from 'lucide-react';

interface ActionPlanModalProps {
  recommendation: Recommendation | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ActionPlanModal: React.FC<ActionPlanModalProps> = ({
  recommendation,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [selectedRanks, setSelectedRanks] = useState<number[]>([1, 2]);
  const [targetSites] = useState<string[]>(
    recommendation?.target_sites || ['North Refinery', 'Processing Unit 4']
  );
  const [startDate, setStartDate] = useState('2026-09-15');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !recommendation) return null;

  const handleToggleRank = (rank: number) => {
    if (selectedRanks.includes(rank)) {
      setSelectedRanks(selectedRanks.filter((r) => r !== rank));
    } else {
      setSelectedRanks([...selectedRanks, rank]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await recommendationService.createActionPlan(
        recommendation.pattern_id,
        selectedRanks,
        targetSites,
        startDate
      );
      onSuccess();
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-xl bg-slate-900 border border-slate-700 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 uppercase tracking-wide">
                Create Action Plan & Intervention
              </h3>
              <p className="text-xs text-slate-400">
                Pattern #{recommendation.pattern_id} — {recommendation.title}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Select Interventions */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
              Select Interventions to Deploy:
            </label>
            <div className="space-y-2">
              {recommendation.recommended_interventions.map((item) => {
                const isSelected = selectedRanks.includes(item.rank);
                return (
                  <div
                    key={item.rank}
                    onClick={() => handleToggleRank(item.rank)}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-purple-950/30 border-purple-500/50 text-slate-100'
                        : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 mt-0.5 ${
                        isSelected
                          ? 'bg-purple-600 border-purple-500 text-white'
                          : 'border-slate-700 bg-slate-900'
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-telemetry uppercase text-purple-300">
                          Priority {item.rank} — {item.control_level}
                        </span>
                      </div>
                      <p className="text-xs text-slate-200 mt-0.5">{item.action}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Target Sites & Start Date */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-blue-400" />
                Target Facilities
              </label>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-300 font-telemetry">
                {targetSites.join(', ')}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-blue-400" />
                Planned Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full p-2 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-purple-500 font-telemetry"
              />
            </div>
          </div>

          {/* Disclaimer */}
          <div className="p-3 rounded bg-blue-950/20 border border-blue-900/40 text-[11px] text-blue-300">
            <strong>Outcome Tracking Enabled:</strong> Precursor rates will be automatically tracked before and after this intervention date to measure historical risk association.
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || selectedRanks.length === 0}
              className="px-5 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 rounded-lg shadow-lg disabled:opacity-50 transition-all flex items-center gap-2"
            >
              {submitting ? 'Creating Plan...' : 'Commit Action Plan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
