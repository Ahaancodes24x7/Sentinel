import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Sparkles,
  CheckCircle,
  FileText,
  Check,
  ShieldAlert,
  UserCheck,
  ChevronDown,
  ChevronUp,
  Layers,
} from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { ReasoningChainVisual } from '../components/common/ReasoningChainVisual';
import { reportsService } from '../services/reportsService';
import { mockReports } from '../data/mockData';
import type { ReportItem, BarrierState3Way } from '../types/sentinel';

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ReportItem | null>(null);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState<'confirm' | 'correct' | 'reject' | 'info'>('confirm');
  const [reviewReason, setReviewReason] = useState('');
  const [correctedBarrierState, setCorrectedBarrierState] = useState<BarrierState3Way>('ABSENT_NOT_CONFIRMED');
  const [ontologyExpanded, setOntologyExpanded] = useState(false);

  useEffect(() => {
    const fetchReport = async () => {
      const { report: r } = await reportsService.getReportById(id || 'SR-10482');
      setReport(r || mockReports[0]);
      if (r?.barrier_state_3way) {
        setCorrectedBarrierState(r.barrier_state_3way);
      }
    };
    fetchReport();
  }, [id]);

  if (!report) {
    return <div className="p-8 text-center text-slate-400 font-telemetry">Loading report details...</div>;
  }

  const handleReviewSubmit = async (action: 'confirm' | 'correct' | 'reject' | 'info') => {
    await reportsService.submitReviewAction(report.report_id, action, reviewReason);
    setReviewSubmitted(true);
  };

  // Helper to render source text with highlighted spans
  const renderHighlightedReportText = () => {
    return (
      <div className="space-y-3">
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-sm leading-relaxed text-slate-200">
          {report.report_id === 'SR-10480' ? (
            <>
              Contractor was observed{' '}
              <mark className="bg-purple-500/20 text-purple-300 px-1 py-0.5 rounded border border-purple-500/40 font-semibold" title="Exposure">
                standing beneath a suspended load
              </mark>{' '}
              while the crane operator{' '}
              <mark className="bg-cyan-500/20 text-cyan-300 px-1 py-0.5 rounded border border-cyan-500/40 font-semibold" title="Activity">
                repositioned the boom
              </mark>
              .{' '}
              <mark className="bg-emerald-500/20 text-emerald-300 px-1 py-0.5 rounded border border-emerald-500/40 font-semibold" title="Actual Outcome">
                No incident occurred
              </mark>
              . Tag lines were not deployed and{' '}
              <mark className="bg-red-500/20 text-red-300 px-1 py-0.5 rounded border border-red-500/40 font-bold" title="Barrier Status">
                no exclusion zone barricade was established
              </mark>
              .
            </>
          ) : report.report_id === 'SR-10481' ? (
            <>
              During{' '}
              <mark className="bg-cyan-500/20 text-cyan-300 px-1 py-0.5 rounded border border-cyan-500/40 font-semibold">
                maintenance on high-pressure hydrocarbon pump P-402B
              </mark>
              , crew initiated line break{' '}
              <mark className="bg-amber-500/20 text-amber-300 px-1 py-0.5 rounded border border-amber-500/40 font-bold">
                prior to verifying mechanical lock-out tag-out
              </mark>
              . Pressure gauge indicated{' '}
              <mark className="bg-purple-500/20 text-purple-300 px-1 py-0.5 rounded border border-purple-500/40 font-semibold">
                4.2 bar residual line pressure
              </mark>
              .
            </>
          ) : (
            <>
              Worker entered the{' '}
              <mark className="bg-cyan-500/20 text-cyan-300 px-1 py-0.5 rounded border border-cyan-500/40 font-semibold">
                elevated pipe rack platform
              </mark>{' '}
              at height{' '}
              <mark className="bg-red-500/20 text-red-300 px-1 py-0.5 rounded border border-red-500/40 font-bold">
                without connecting the fall-arrest lanyard
              </mark>{' '}
              to the certified anchor point. Scaffolding deck{' '}
              <mark className="bg-purple-500/20 text-purple-300 px-1 py-0.5 rounded border border-purple-500/40 font-semibold">
                missing toe boards on west elevation
              </mark>
              .
            </>
          )}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-3 text-[11px] font-telemetry pt-1 text-slate-400">
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded bg-cyan-400" />
            <span>Activity</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded bg-amber-400" />
            <span>Energy Source</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded bg-red-400" />
            <span>Barrier Failure / Absent</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded bg-purple-400" />
            <span>Exposure Pathway</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded bg-emerald-400" />
            <span>Actual Outcome</span>
          </span>
        </div>
      </div>
    );
  };

  const barrierState = report.barrier_state_3way || 'ABSENT_NOT_CONFIRMED';

  return (
    <div className="space-y-6">
      {/* Header & Back Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/reports')}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xl font-black font-telemetry text-blue-400">
                {report.report_id}
              </span>
              <RiskBadge level={report.risk_level} size="md" />
              <span className="text-xs font-telemetry font-bold text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
                {report.source.toUpperCase()} DATASOURCE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-3 font-telemetry">
              <span>Facility: <strong className="text-slate-200">{report.site}</strong></span>
              <span>•</span>
              <span>Logged: <strong className="text-slate-200">{new Date(report.timestamp).toLocaleString()}</strong></span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-xs font-telemetry px-3 py-1 rounded border font-bold ${reviewSubmitted
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}>
            Status: {reviewSubmitted ? 'REVIEWED (QUEUED FOR TRAINING)' : report.review_status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* HERO SECTION: TWO-COLUMN MAIN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT COLUMN: ORIGINAL REPORT TEXT & EXTRACTION SPANS */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" />
              Original Safety Observation Text
            </h3>
            <span className="text-[10px] font-telemetry text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
              Annotated Evidence Spans
            </span>
          </div>

          {renderHighlightedReportText()}

          {/* SIF POTENTIAL VS ACTUAL OUTCOME BANNER */}
          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
            <div className="flex items-center justify-between text-xs font-telemetry">
              <span className="text-slate-400 uppercase font-semibold">Actual Outcome Severity</span>
              <span className="text-emerald-400 font-bold">
                {report.actual_outcome === 'NO_INJURY' ? 'NO INJURY (NEAR-MISS)' : 'NO INJURY'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs font-telemetry pt-1 border-t border-slate-800/60">
              <span className="text-slate-400 uppercase font-semibold">Assessed SIF Potential</span>
              <span className="text-red-400 font-extrabold">HIGH SIF POTENTIAL (CRITICAL)</span>
            </div>
            <div className="text-[11px] text-amber-300/90 italic pt-1">
              "Outcome severity and SIF potential are independent. High energy exposure existed with an unconfirmed barrier."
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: EXTRACTED SAFETY EVENT & 3-WAY BARRIER PANEL */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              Extracted Safety Event
            </h3>
            <span className="text-[11px] font-telemetry text-emerald-400 font-bold">
              Confidence: {Math.round((report.classification?.confidence || 0.94) * 100)}%
            </span>
          </div>

          <div className="space-y-3 font-telemetry text-xs">
            {/* Activity */}
            <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 font-semibold uppercase">Activity</span>
              <span className="text-slate-200 font-bold">
                {report.extracted_fields?.activity?.text || 'Crane Hoist Operation / Pipe Rack'}
              </span>
            </div>

            {/* Energy */}
            <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 font-semibold uppercase">Energy Source</span>
              <span className="text-amber-400 font-bold">
                {report.extracted_fields?.energy_type?.label || 'Gravitational Energy (>4m Fall)'}
              </span>
            </div>

            {/* 3-WAY BARRIER STATE */}
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 font-semibold uppercase">Barrier Name</span>
                <span className="text-slate-200 font-bold">
                  {report.failed_barrier || 'Fall Protection Verification'}
                </span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-slate-800/80">
                <span className="text-slate-400 font-semibold uppercase">3-Way Barrier Status</span>
                {barrierState === 'CONFIRMED_EFFECTIVE' ? (
                  <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    CONFIRMED EFFECTIVE
                  </span>
                ) : barrierState === 'UNCERTAIN_DEGRADED' ? (
                  <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    UNCERTAIN / DEGRADED
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700">
                    ABSENT / NOT CONFIRMED
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500 italic pt-1">
                "Absence of evidence is not automatically treated as evidence of an effective barrier."
              </div>
            </div>

            {/* Exposure */}
            <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 font-semibold uppercase">Exposure Pathway</span>
              <span className="text-purple-300 font-bold">
                {report.extracted_fields?.exposure?.text || 'Unprotected worker in line of fire'}
              </span>
            </div>

            {/* Credible Consequence */}
            <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 font-semibold uppercase">Credible Consequence</span>
              <span className="text-red-400 font-extrabold">
                {report.extracted_fields?.credible_consequence?.label || 'Fatal Fall from Elevation / Crush Injury'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* WHY SENTINEL FLAGGED THIS PANEL & LIFE-SAVING RULE ONTOLOGY */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* WHY SENTINEL FLAGGED THIS (2 cols) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              <span>Why Sentinel Flagged This</span>
            </h3>
            <span className="text-[11px] font-telemetry text-slate-400">
              Step-by-step reasoning justification
            </span>
          </div>

          <div className="space-y-2 text-xs font-telemetry">
            {(report.why_flagged_checklist || [
              'High-energy source detected (Gravitational Fall >4m / Heavy Load)',
              'Person exposed to uncontained hazard pathway',
              'Critical safety barrier absent or unconfirmed in observation text',
              'Credible severe outcome identified (Fatal Impact / Severe Disablement)',
              'Similar precursor patterns detected across site operations',
            ]).map((item, idx) => (
              <div key={idx} className="flex items-center space-x-2.5 p-2 rounded bg-slate-950 border border-slate-800/80">
                <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span className="text-slate-200 font-medium">{item}</span>
              </div>
            ))}
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between text-xs font-telemetry pt-2">
            <div>
              <span className="text-slate-400 uppercase font-semibold">SIF Potential: </span>
              <strong className="text-red-400 font-black">HIGH</strong>
              <span className="mx-2 text-slate-700">|</span>
              <span className="text-slate-400 uppercase font-semibold">Confidence: </span>
              <strong className="text-emerald-400 font-bold">94%</strong>
            </div>
            <span className="text-[10px] text-slate-500">
              Explanation generated from extracted structured fields.
            </span>
          </div>
        </div>

        {/* LIFE-SAVING RULE ONTOLOGY CARD (1 col) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center space-x-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              <span>Life-Saving Rule Mapping</span>
            </h3>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center space-y-1">
            <div className="text-[10px] font-telemetry text-slate-400 uppercase tracking-wider font-semibold">
              IOGP Life-Saving Rule #1
            </div>
            <div className="text-base font-black text-emerald-400 font-telemetry">
              {report.lsr_tag.toUpperCase()}
            </div>
          </div>

          <div className="space-y-2 text-xs font-telemetry text-slate-300">
            <div className="flex justify-between p-2 bg-slate-950 rounded border border-slate-800">
              <span className="text-slate-500">Activity Basis:</span>
              <span className="font-semibold text-slate-200">Elevated Work</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-950 rounded border border-slate-800">
              <span className="text-slate-500">Energy Basis:</span>
              <span className="font-semibold text-amber-300">Gravity / Fall Potential</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-950 rounded border border-slate-800">
              <span className="text-slate-500">Barrier Basis:</span>
              <span className="font-semibold text-red-300">Fall Protection</span>
            </div>
          </div>

          <button
            onClick={() => setOntologyExpanded(!ontologyExpanded)}
            className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-telemetry text-xs font-bold transition-colors flex items-center justify-between"
          >
            <span>Auditable Ontology Mapping</span>
            {ontologyExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {ontologyExpanded && (
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] font-telemetry space-y-1 text-slate-400">
              <div>Energy Type &rarr; <strong className="text-amber-300">Gravity</strong></div>
              <div>Activity &rarr; <strong className="text-cyan-300">Working at Height</strong></div>
              <div>LSR &rarr; <strong className="text-emerald-300">Working at Height</strong></div>
            </div>
          )}
        </div>
      </div>

      {/* FULL CAUSALITY REASONING CHAIN */}
      <ReasoningChainVisual />

      {/* HSE REVIEW WORKFLOW PANEL & RESPONSIBLE AI WORKFLOW */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry flex items-center space-x-2">
              <UserCheck className="w-4 h-4 text-blue-400" />
              <span>HSE Reviewer Action & Model Fine-Tuning Queue</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Human-in-the-Loop review ensures zero uncalibrated model decisions reach operational reporting.
            </p>
          </div>
        </div>

        {/* RESPONSIBLE AI WORKFLOW VISUALIZATION */}
        <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-telemetry space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">
            Responsible AI Governance Flow
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-300 font-semibold">
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-blue-300">AI Detection</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-blue-300">Confidence Assessment</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-blue-300">Automatic Routing</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-amber-300">HSE Review</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-emerald-300">Confirmed / Corrected</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-purple-300">Retraining Queue</span> &rarr;
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-400">Future Model Training</span>
          </div>
        </div>

        {/* REVIEW BUTTONS & FORM */}
        {!reviewSubmitted ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setActiveTab('confirm')}
                className={`px-4 py-2 rounded-lg font-telemetry text-xs font-bold transition-all ${activeTab === 'confirm'
                    ? 'bg-emerald-600 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
              >
                [CONFIRM SIF POTENTIAL]
              </button>
              <button
                onClick={() => setActiveTab('correct')}
                className={`px-4 py-2 rounded-lg font-telemetry text-xs font-bold transition-all ${activeTab === 'correct'
                    ? 'bg-amber-600 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
              >
                [CORRECT CLASSIFICATION]
              </button>
              <button
                onClick={() => setActiveTab('reject')}
                className={`px-4 py-2 rounded-lg font-telemetry text-xs font-bold transition-all ${activeTab === 'reject'
                    ? 'bg-red-600 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
              >
                [REJECT]
              </button>
              <button
                onClick={() => setActiveTab('info')}
                className={`px-4 py-2 rounded-lg font-telemetry text-xs font-bold transition-all ${activeTab === 'info'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
              >
                [NEEDS MORE INFORMATION]
              </button>
            </div>

            {/* CORRECTION FIELD EDITS IF ACTIVE */}
            {activeTab === 'correct' && (
              <div className="p-4 bg-slate-950 rounded-xl border border-amber-500/30 space-y-3">
                <div className="text-xs font-bold text-amber-300 uppercase font-telemetry">
                  Modify Extracted Safety Fields
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Corrected 3-Way Barrier Status</label>
                    <select
                      value={correctedBarrierState}
                      onChange={(e) => setCorrectedBarrierState(e.target.value as BarrierState3Way)}
                      className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-200 font-telemetry"
                    >
                      <option value="CONFIRMED_EFFECTIVE">CONFIRMED EFFECTIVE</option>
                      <option value="UNCERTAIN_DEGRADED">UNCERTAIN / DEGRADED</option>
                      <option value="ABSENT_NOT_CONFIRMED">ABSENT / NOT CONFIRMED</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-telemetry font-bold text-slate-300 uppercase">
                HSE Review Reason / Audit Notes (Required)
              </label>
              <textarea
                value={reviewReason}
                onChange={(e) => setReviewReason(e.target.value)}
                placeholder="Enter technical rationale for HSE review decision..."
                className="w-full h-20 bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <button
              onClick={() => handleReviewSubmit(activeTab)}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-telemetry text-xs font-bold transition-all shadow-lg"
            >
              Submit Review & Enqueue for Model Retraining
            </button>
          </div>
        ) : (
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-xl space-y-2 font-telemetry text-xs text-emerald-200">
            <div className="flex items-center space-x-2 font-bold text-emerald-400">
              <CheckCircle className="w-5 h-5" />
              <span>Review Submitted & Logged</span>
            </div>
            <div>Reviewed by: <strong>HSE Analyst (Shell Ops)</strong></div>
            <div>Timestamp: <strong>{new Date().toLocaleString()}</strong></div>
            <div>Model Version: <strong>Sentinel-NLP v0.4</strong></div>
            <div className="mt-2 inline-block px-3 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
              ✓ Added to retraining queue
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
