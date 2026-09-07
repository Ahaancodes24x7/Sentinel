import React from 'react';
import { Cpu, Database, Sparkles, Server, ShieldCheck, Info } from 'lucide-react';
import { mockModelPerformance } from '../data/mockData';

export const ModelPerformancePage: React.FC = () => {
  const data = mockModelPerformance;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              SIF NLP Engine — ML Evaluation & Governance
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Precision, Recall (F2), PR-AUC, LSR Mapping, Extraction F1 scores, Calibration Error, and Data Transparency disclosures.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-telemetry self-start sm:self-auto">
          <span className="px-3 py-1 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-bold">
            Engine: {data.model_version}
          </span>
          <span className="px-3 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5" />
            Inference: {data.inference_latency_ms}ms
          </span>
        </div>
      </div>

      {/* 1. DATASET & MODEL TRANSPARENCY DISCLOSURE */}
      <div className="bg-slate-900/90 border border-blue-500/30 rounded-xl p-4 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <span className="p-2 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <Info className="w-5 h-5" />
          </span>
          <div>
            <div className="text-xs font-extrabold text-blue-300 font-telemetry uppercase tracking-wider">
              Data & Model Status Disclosure
            </div>
            <div className="text-xs text-slate-300 font-telemetry">
              Dataset: <strong>Synthetic Demonstration Dataset</strong> &bull; Status: <span className="text-amber-400 font-bold">DEMO DATA — NOT OIL PRODUCTION DATA</span>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 font-telemetry bg-slate-950 px-3 py-1.5 rounded border border-slate-800">
          Designed for integration with OIL HSSE exports / approved interfaces.
        </div>
      </div>

      {/* 2. RECALL-PRIORITIZED REASONING BANNER */}
      <div className="bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border-l-4 border-emerald-500 border-y border-r border-slate-800 rounded-r-xl p-4 space-y-1 font-telemetry">
        <div className="flex items-center space-x-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" />
          <span>Core Evaluation Strategy: SIF Recall Priority</span>
        </div>
        <p className="text-xs text-slate-300">
          <strong className="text-emerald-300">Recall is prioritized (Target &gt;95%)</strong> because missing a genuine SIF precursor is exponentially more costly than generating an additional review for HSE analysts.
        </p>
      </div>

      {/* 3. HERO EVALUATION METRICS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-telemetry">
        {/* SIF RECALL */}
        <div className="p-5 rounded-xl bg-slate-900 border border-emerald-500/40 shadow-xl space-y-1">
          <div className="text-[10px] font-bold text-emerald-400 uppercase">SIF DETECTION RECALL</div>
          <div className="text-3xl font-black text-emerald-400">{data.sif_classifier.recall}%</div>
          <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
            F2 Score: <strong className="text-slate-200">{data.sif_classifier.f2}</strong> (High Recall Weight)
          </div>
        </div>

        {/* SIF PRECISION */}
        <div className="p-5 rounded-xl bg-slate-900 border border-blue-500/40 shadow-xl space-y-1">
          <div className="text-[10px] font-bold text-blue-400 uppercase">SIF PRECISION & PR-AUC</div>
          <div className="text-3xl font-black text-blue-400">{data.sif_classifier.precision}%</div>
          <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
            PR-AUC: <strong className="text-slate-200">{data.sif_classifier.pr_auc}</strong>
          </div>
        </div>

        {/* LSR MAPPING TOP-1 */}
        <div className="p-5 rounded-xl bg-slate-900 border border-purple-500/40 shadow-xl space-y-1">
          <div className="text-[10px] font-bold text-purple-300 uppercase">LSR TOP-1 / TOP-2 ACCURACY</div>
          <div className="text-3xl font-black text-purple-300">{data.lsr_classifier.top1_accuracy}%</div>
          <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
            Top-2 Accuracy: <strong className="text-slate-200">{data.lsr_classifier.top2_accuracy}%</strong>
          </div>
        </div>

        {/* CALIBRATION ERROR */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-700 shadow-xl space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">EXPECTED CALIBRATION ERROR (ECE)</div>
          <div className="text-3xl font-black text-slate-100">{data.calibration.expected_calibration_error}</div>
          <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
            Well-calibrated probabilities
          </div>
        </div>
      </div>

      {/* 4. FIELD EXTRACTION F1 & CONFUSION MATRIX */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ENTITY EXTRACTION F1 BREAKDOWN */}
        <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-5 space-y-4 shadow-2xl">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Entity Extraction F1 Breakdown</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Structured field extraction precision and recall across NLP spans.
            </p>
          </div>

          <div className="space-y-3 font-telemetry text-xs">
            <div>
              <div className="flex justify-between mb-1 font-bold">
                <span className="text-cyan-300">Activity Extraction F1</span>
                <span className="text-slate-100">{data.extraction_f1.activity_f1}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${data.extraction_f1.activity_f1}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1 font-bold">
                <span className="text-amber-300">Energy Type Extraction F1</span>
                <span className="text-slate-100">{data.extraction_f1.energy_f1}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                <div className="h-full bg-amber-400 rounded-full" style={{ width: `${data.extraction_f1.energy_f1}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1 font-bold">
                <span className="text-red-300">Barrier Detection F1</span>
                <span className="text-slate-100">{data.extraction_f1.barrier_f1}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                <div className="h-full bg-red-400 rounded-full" style={{ width: `${data.extraction_f1.barrier_f1}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1 font-bold">
                <span className="text-purple-300">Exposure Pathway F1</span>
                <span className="text-slate-100">{data.extraction_f1.exposure_f1}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                <div className="h-full bg-purple-400 rounded-full" style={{ width: `${data.extraction_f1.exposure_f1}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* CONFUSION MATRIX & QUEUE STATS */}
        <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-5 space-y-4 shadow-2xl">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center space-x-2">
              <Database className="w-4 h-4 text-blue-400" />
              <span>Confusion Matrix & Review Queue Metrics</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Evaluated on 24,500 synthetic demonstration safety observations.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 font-telemetry text-xs">
            <div className="p-3.5 bg-emerald-950/20 rounded-xl border border-emerald-500/40 text-center">
              <span className="text-[10px] text-emerald-400 font-bold uppercase block">True Positives (TP)</span>
              <span className="text-2xl font-black text-slate-100">{data.confusion_matrix.tp}</span>
            </div>

            <div className="p-3.5 bg-amber-950/20 rounded-xl border border-amber-500/40 text-center">
              <span className="text-[10px] text-amber-400 font-bold uppercase block">False Positives (FP)</span>
              <span className="text-2xl font-black text-slate-100">{data.confusion_matrix.fp}</span>
              <span className="text-[9px] text-slate-400 block mt-0.5">Routed to Review Queue</span>
            </div>

            <div className="p-3.5 bg-red-950/20 rounded-xl border border-red-500/40 text-center">
              <span className="text-[10px] text-red-400 font-bold uppercase block">False Negatives (FN)</span>
              <span className="text-2xl font-black text-red-400">{data.confusion_matrix.fn}</span>
              <span className="text-[9px] text-slate-400 block mt-0.5">Minimizing FN is priority #1</span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase block">True Negatives (TN)</span>
              <span className="text-2xl font-black text-slate-100">{data.confusion_matrix.tn}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
