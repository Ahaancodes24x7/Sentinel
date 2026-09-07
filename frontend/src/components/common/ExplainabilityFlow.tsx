import React from 'react';
import {
  FileText,
  Flame,
  ShieldX,
  Layers,
  AlertOctagon,
  CheckCircle,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import type { ReportItem } from '../../types/sentinel';

interface ExplainabilityFlowProps {
  report: ReportItem;
}

export const ExplainabilityFlow: React.FC<ExplainabilityFlowProps> = ({ report }) => {
  const steps = [
    {
      step: 1,
      title: 'NLP Evidence Extracted',
      icon: FileText,
      color: 'border-blue-500/40 bg-blue-500/10 text-blue-400',
      badge: 'Span Extractor v2.4',
      details: [
        { label: 'Activity', val: report.extracted_fields?.activity?.text || 'Elevated Deck Work' },
        { label: 'Energy Source', val: report.extracted_fields?.energy_type?.label || 'Gravitational Energy' },
        { label: 'Observed Exposure', val: report.extracted_fields?.exposure?.text || 'Direct Exposure at Height' },
      ],
    },
    {
      step: 2,
      title: 'Hazard Classification',
      icon: Flame,
      color: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
      badge: `${Math.round((report.classification?.confidence || 0.94) * 100)}% Confidence`,
      details: [
        { label: 'Primary Hazard', val: report.hazard || 'Working at Height' },
        { label: 'LSR Rule Tag', val: report.lsr_tag || 'Working at Height' },
        { label: 'Source File', val: report.source },
      ],
    },
    {
      step: 3,
      title: 'Safety Barrier Analysis',
      icon: ShieldX,
      color: 'border-red-500/40 bg-red-500/10 text-red-400',
      badge: 'FAILED BARRIER',
      details: [
        { label: 'Failed Control', val: report.failed_barrier },
        { label: 'Control State', val: report.extracted_fields?.barrier_status?.text || 'Unverified / Unattached' },
        { label: 'Barrier Criticality', val: 'Level-1 Safety Control' },
      ],
    },
    {
      step: 4,
      title: 'Precursor Pattern Correlation',
      icon: Layers,
      color: 'border-purple-500/40 bg-purple-500/10 text-purple-400',
      badge: 'Pattern #P-019',
      details: [
        { label: 'Correlated Cluster', val: 'P-019 Fall Protection Degradation' },
        { label: 'Historical Matches', val: '127 events across 4 sites' },
        { label: 'Growth Velocity', val: '+42% in 30 days' },
      ],
    },
    {
      step: 5,
      title: 'SIF Escalation Evaluation',
      icon: AlertOctagon,
      color: 'border-red-600 bg-red-600/20 text-red-300',
      badge: report.risk_level,
      details: [
        { label: 'SIF Potential', val: report.sif_potential ? 'YES — CRITICAL' : 'LOW' },
        { label: 'Overall Confidence', val: `${Math.round((report.classification?.confidence || 0.94) * 100)}%` },
        { label: 'Model Version', val: report.classification?.model_version || 'baseline2-v0.3' },
      ],
    },
  ];

  return (
    <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
              Why Did Sentinel Flag This?
            </h3>
            <p className="text-xs text-slate-400">
              Complete AI reasoning and evidence trail behind SIF classification decision
            </p>
          </div>
        </div>
        <div className="text-xs font-telemetry bg-slate-800 text-slate-300 px-2.5 py-1 rounded border border-slate-700">
          Confidence: <span className="text-emerald-400 font-bold">{Math.round((report.classification?.confidence || 0.94) * 100)}%</span>
        </div>
      </div>

      {/* Step Progress Line */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {steps.map((s, idx) => {
          const StepIcon = s.icon;
          return (
            <div
              key={s.step}
              className="relative flex flex-col justify-between rounded-lg bg-slate-950/70 border border-slate-800 p-3 hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold font-telemetry text-slate-500">
                    STAGE 0{s.step}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${s.color}`}>
                    {s.badge}
                  </span>
                </div>

                <div className="flex items-center gap-2 mb-2">
                  <div className={`p-1.5 rounded ${s.color}`}>
                    <StepIcon className="w-3.5 h-3.5" />
                  </div>
                  <h4 className="text-xs font-bold text-slate-200 line-clamp-1">{s.title}</h4>
                </div>

                <div className="space-y-1.5 text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                  {s.details.map((d, i) => (
                    <div key={i} className="flex justify-between items-start gap-1">
                      <span className="text-slate-500 shrink-0">{d.label}:</span>
                      <span className="text-slate-200 font-medium text-right line-clamp-1 font-telemetry">{d.val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-slate-600">
                  <ChevronRight className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Justification summary box */}
      <div className="mt-4 p-3 rounded bg-red-950/30 border border-red-900/40 text-xs text-red-200 flex items-start gap-2.5">
        <CheckCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-red-400 uppercase tracking-wide font-telemetry mr-2">
            Sentinel AI Audit Summary:
          </span>
          {report.classification?.justification ||
            'Flagged as SIF Precursor due to unverified fall protection controls, high-gravitational elevation exposure, and 42% historical pattern escalation.'}
        </div>
      </div>
    </div>
  );
};
