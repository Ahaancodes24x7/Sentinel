import React, { useState } from 'react';
import { Activity, Zap, ShieldOff, Eye, AlertOctagon, ShieldCheck, ChevronRight, Info } from 'lucide-react';
import type { ReasoningChainStep } from '../../types/sentinel';

interface ReasoningChainVisualProps {
  steps?: ReasoningChainStep[];
  onNodeClick?: (step: ReasoningChainStep) => void;
}

const defaultSteps: ReasoningChainStep[] = [
  {
    id: 'activity',
    title: 'ACTIVITY',
    subtitle: 'Task / Operation',
    value: 'Working at Height / Pipe Rack',
    confidence: 0.94,
    source_text: 'Worker entered the elevated pipe rack platform at height...',
    ontology_mapping: 'Activity -> Working at Height (>4m)',
    status: 'detected',
  },
  {
    id: 'energy',
    title: 'ENERGY',
    subtitle: 'Hazardous Energy Source',
    value: 'Gravitational Energy (>4m Fall)',
    confidence: 0.95,
    source_text: 'elevated pipe rack platform at height without tie-off',
    ontology_mapping: 'Energy -> Gravitational Energy (Fall Hazard)',
    status: 'critical',
  },
  {
    id: 'barrier',
    title: 'BARRIER',
    subtitle: 'Safety Control State',
    value: 'Fall Protection Lanyard — NOT CONFIRMED',
    confidence: 0.96,
    source_text: 'without connecting the fall-arrest lanyard to certified anchor',
    ontology_mapping: 'Barrier -> Primary Protection (Fall Arrest)',
    status: 'ABSENT_NOT_CONFIRMED',
  },
  {
    id: 'exposure',
    title: 'EXPOSURE',
    subtitle: 'Personnel Hazard Pathway',
    value: 'Unprotected Worker at Deck Edge',
    confidence: 0.92,
    source_text: 'standing at platform edge without harness tie-off',
    ontology_mapping: 'Exposure -> Direct Exposure Pathway',
    status: 'critical',
  },
  {
    id: 'consequence',
    title: 'CONSEQUENCE',
    subtitle: 'Credible Worst-Case Impact',
    value: 'Potential Fatal Fall from Elevation',
    confidence: 0.95,
    source_text: 'Credible worst-case impact: Fatal gravity strike/fall',
    ontology_mapping: 'Consequence -> Fatality / Severe Disability',
    status: 'critical',
  },
  {
    id: 'lsr',
    title: 'LIFE-SAVING RULE',
    subtitle: 'IOGP Standard Mapping',
    value: 'Working at Height',
    confidence: 0.98,
    source_text: 'Mapped to IOGP Life-Saving Rule #1',
    ontology_mapping: 'LSR -> Working at Height',
    status: 'detected',
  },
];

export const ReasoningChainVisual: React.FC<ReasoningChainVisualProps> = ({
  steps = defaultSteps,
  onNodeClick,
}) => {
  const [selectedStep, setSelectedStep] = useState<ReasoningChainStep>(steps[0]);

  const handleSelect = (step: ReasoningChainStep) => {
    setSelectedStep(step);
    if (onNodeClick) onNodeClick(step);
  };

  const getIcon = (id: string) => {
    switch (id) {
      case 'activity': return <Activity className="w-4 h-4 text-cyan-400" />;
      case 'energy': return <Zap className="w-4 h-4 text-amber-400" />;
      case 'barrier': return <ShieldOff className="w-4 h-4 text-red-400" />;
      case 'exposure': return <Eye className="w-4 h-4 text-purple-400" />;
      case 'consequence': return <AlertOctagon className="w-4 h-4 text-red-500" />;
      case 'lsr': return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      default: return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getBorderColor = (step: ReasoningChainStep) => {
    if (step.id === selectedStep.id) return 'border-blue-500 ring-2 ring-blue-500/30 bg-blue-950/40';
    if (step.status === 'ABSENT_NOT_CONFIRMED' || step.status === 'critical') return 'border-red-500/40 hover:border-red-400 bg-red-950/10';
    return 'border-slate-800 hover:border-slate-600 bg-slate-900/60';
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-telemetry">
              Sentinel SIF Reasoning Chain
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Step-by-step causality reasoning: <span className="text-cyan-300">Activity</span> &rarr; <span className="text-amber-300">Energy</span> &rarr; <span className="text-red-300">Barrier</span> &rarr; <span className="text-purple-300">Exposure</span> &rarr; <span className="text-red-400">Consequence</span> &rarr; <span className="text-emerald-300">Life-Saving Rule</span>
          </p>
        </div>
        <span className="text-[11px] font-telemetry px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
          Click any node to inspect evidence
        </span>
      </div>

      {/* Chain Nodes Flow */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-2 relative my-2">
        {steps.map((step) => (
          <div key={step.id} className="relative flex flex-col">
            <button
              onClick={() => handleSelect(step)}
              className={`flex-1 p-3 rounded-lg border text-left transition-all duration-200 cursor-pointer flex flex-col justify-between ${getBorderColor(
                step
              )}`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="p-1 rounded bg-slate-800/80 border border-slate-700">
                    {getIcon(step.id)}
                  </span>
                  <span className="text-[10px] font-telemetry font-bold text-slate-400">
                    {Math.round(step.confidence * 100)}%
                  </span>
                </div>
                <div className="text-[10px] font-telemetry tracking-wider text-slate-400 font-semibold uppercase">
                  {step.title}
                </div>
                <div className="text-xs font-bold text-slate-200 line-clamp-2 mt-1 leading-tight">
                  {step.value}
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-800/60">
                <span className="truncate">{step.subtitle}</span>
                <ChevronRight className="w-3 h-3 text-slate-500 flex-shrink-0 ml-1" />
              </div>
            </button>
          </div>
        ))}
      </div>

      {/* Selected Node Deep Dive Inspection */}
      {selectedStep && (
        <div className="mt-4 p-3.5 bg-slate-950/80 rounded-lg border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1 flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-telemetry font-bold text-cyan-400 uppercase tracking-wider">
                Extracted Evidence Node: {selectedStep.title}
              </span>
              <span className="text-[11px] font-telemetry text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                Confidence: {(selectedStep.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-slate-300 font-mono bg-slate-900/90 p-2 rounded border border-slate-800">
              "{selectedStep.source_text}"
            </p>
          </div>
          <div className="space-y-1 md:text-right border-t md:border-t-0 md:border-l border-slate-800 pt-2 md:pt-0 md:pl-4 min-w-[220px]">
            <div className="text-[11px] font-telemetry text-slate-400 uppercase font-semibold">
              Ontology Mapping Rule
            </div>
            <div className="text-xs font-bold text-blue-300 font-telemetry">
              {selectedStep.ontology_mapping}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
