import React, { useState } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  ShieldAlert,
  ShieldX,
  Layers,
  Sparkles,
  ArrowUpRight,
  Info,
  SlidersHorizontal,
  CheckCircle2,
  HelpCircle,
  Play,
} from 'lucide-react';
import { KPICard } from '../components/common/KPICard';
import { DataTable } from '../components/common/DataTable';
import type { Column } from '../components/common/DataTable';
import { SafetyBriefModal } from '../components/common/SafetyBriefModal';
import { ReasoningChainVisual } from '../components/common/ReasoningChainVisual';
import { SifOutcomeMatrix } from '../components/common/SifOutcomeMatrix';
import {
  mockSummary,
  mockReports,
  mockDemoScenarios,
} from '../data/mockData';
import type { ReportItem } from '../types/sentinel';

export const DashboardPage: React.FC = () => {
  const { selectedSite } = useOutletContext<{ selectedSite: string }>();
  const [dateRange, setDateRange] = useState<'24H' | '7D' | '30D' | '90D'>('30D');
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  const [metricToggle, setMetricToggle] = useState<'ratio' | 'composite'>('ratio');
  const [selectedBucketFilter, setSelectedBucketFilter] = useState<string | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  const navigate = useNavigate();

  // Filter reports by site and bucket
  let filteredReports = selectedSite === 'All Sites'
    ? mockReports
    : mockReports.filter((r) => r.site.toLowerCase() === selectedSite.toLowerCase());

  if (selectedBucketFilter) {
    filteredReports = filteredReports.filter((r) => r.bucket === selectedBucketFilter);
  }

  // Column specs for recent reports
  const recentReportColumns: Column<ReportItem>[] = [
    {
      header: 'Report ID',
      accessorKey: 'report_id',
      sortable: true,
      cell: (row) => (
        <button
          onClick={() => navigate(`/reports/${row.report_id}`)}
          className="font-telemetry font-bold text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-2 py-0.5 rounded border border-blue-500/20 transition-colors"
        >
          {row.report_id}
        </button>
      ),
    },
    {
      header: 'Timestamp',
      accessorKey: 'timestamp',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry text-slate-400 text-[11px]">
          {new Date(row.timestamp).toLocaleString('en-US', {
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    { header: 'Site', accessorKey: 'site', sortable: true },
    { header: 'Hazard Category', accessorKey: 'hazard', sortable: true },
    {
      header: 'Actual Outcome',
      accessorKey: 'actual_outcome',
      cell: (row) => (
        <span className="font-telemetry font-medium text-xs text-slate-300">
          {row.actual_outcome === 'NO_INJURY' ? 'No Injury (Near-Miss)' : row.actual_outcome || 'No Injury'}
        </span>
      ),
    },
    {
      header: 'SIF Potential',
      accessorKey: 'sif_potential',
      sortable: true,
      cell: (row) => (
        <span
          className={`font-telemetry font-bold text-xs px-2 py-0.5 rounded border ${row.sif_potential
              ? 'bg-red-500/10 text-red-400 border-red-500/30'
              : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
        >
          {row.sif_potential ? 'HIGH SIF' : 'NON-SIF'}
        </span>
      ),
    },
    {
      header: '3-Way Barrier State',
      accessorKey: 'barrier_state_3way',
      cell: (row) => {
        const state = row.barrier_state_3way || 'ABSENT_NOT_CONFIRMED';
        if (state === 'CONFIRMED_EFFECTIVE') {
          return (
            <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              EFFECTIVE
            </span>
          );
        }
        if (state === 'UNCERTAIN_DEGRADED') {
          return (
            <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              DEGRADED
            </span>
          );
        }
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-slate-800 text-slate-400 border border-slate-700">
            NOT CONFIRMED
          </span>
        );
      },
    },
    {
      header: 'Confidence',
      accessorKey: 'classification',
      cell: (row) => (
        <span className="font-telemetry font-bold text-emerald-400">
          {Math.round((row.classification?.confidence || 0.94) * 100)}%
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* 1. DEMO SCENARIO SELECTOR BAR */}
      <div className="bg-slate-900/90 border border-blue-500/30 rounded-xl p-3.5 backdrop-blur-md flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center space-x-2">
          <span className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/40">
            <Play className="w-4 h-4 fill-blue-400" />
          </span>
          <div>
            <div className="text-xs font-bold text-slate-100 font-telemetry uppercase tracking-wider">
              Interactive SIH Presentation Scenarios
            </div>
            <div className="text-[11px] text-slate-400">
              Select a pre-loaded near-miss case study to demonstrate end-to-end NLP reasoning & barrier mapping
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {mockDemoScenarios.map((sc) => (
            <button
              key={sc.id}
              onClick={() => navigate(`/reports/${sc.reportId}`)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-blue-600/30 border border-slate-700 hover:border-blue-500/50 text-xs font-telemetry font-semibold text-slate-200 hover:text-blue-300 transition-all flex items-center space-x-1.5"
            >
              <span>{sc.name.split(':')[0]}</span>
              <ArrowUpRight className="w-3 h-3 text-slate-400" />
            </button>
          ))}
        </div>
      </div>

      {/* 2. PROMINENT SENTINEL INTELLIGENCE BANNER */}
      <div className="bg-gradient-to-r from-red-950/40 via-slate-900 to-slate-900 border-l-4 border-red-500 border-y border-r border-slate-800 rounded-r-xl p-5 shadow-2xl space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className="p-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <div>
              <h2 className="text-base font-extrabold text-slate-100 uppercase tracking-wider font-telemetry">
                SENTINEL SAFETY INTELLIGENCE
              </h2>
              <div className="text-sm font-bold text-red-400 font-telemetry">
                "23 high-energy precursor situations require HSE review."
              </div>
            </div>
          </div>
          <span className="hidden sm:inline-block px-3 py-1 rounded-full text-xs font-telemetry font-bold bg-red-500/10 text-red-400 border border-red-500/30">
            Action Required
          </span>
        </div>
        <p className="text-xs text-slate-300 pl-11">
          <strong className="text-amber-300">Important:</strong> SIF potential is assessed from energy exposure and barrier effectiveness — independent of whether an injury actually occurred.
        </p>
      </div>

      {/* 3. HEADER & CONTROLS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry flex items-center space-x-2">
            <span>SIF Precursor Command Center</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30 font-telemetry">
              LIVE TELEMETRY
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time SIF precursor identification, safety barrier status, and pattern intelligence across assets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Ratio vs Composite Metric Toggle */}
          <div className="relative flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              onClick={() => setMetricToggle('ratio')}
              className={`px-3 py-1 rounded font-telemetry font-bold transition-all ${metricToggle === 'ratio'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Simple PSIF Ratio
            </button>
            <button
              onClick={() => setMetricToggle('composite')}
              className={`px-3 py-1 rounded font-telemetry font-bold transition-all ${metricToggle === 'composite'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              Composite Indicator
            </button>
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="ml-1 p-1 text-slate-400 hover:text-amber-300"
            >
              <Info className="w-3.5 h-3.5" />
            </button>

            {/* SME Calibration Tooltip */}
            {showTooltip && (
              <div className="absolute right-0 top-10 w-72 p-3 bg-slate-900 border border-amber-500/40 rounded-xl shadow-2xl z-50 text-xs text-slate-300">
                <div className="font-bold text-amber-400 mb-1 font-telemetry">
                  Composite Indicator — Tunable
                </div>
                This indicator combines precursor rate, recurring barrier failures and energy-magnitude class. Weights are configurable and require calibration with OIL HSE SMEs.
              </div>
            )}
          </div>

          {/* Timeframe Selector */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            {(['24H', '7D', '30D', '90D'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-2.5 py-1 rounded font-telemetry font-bold transition-all ${dateRange === range
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-white'
                  }`}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Generate Brief Button */}
          <button
            onClick={() => setBriefModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg transition-all font-telemetry"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-200" />
            Generate Brief
          </button>
        </div>
      </div>

      {/* 4. PS 26165 SPECIFIC KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <KPICard
          title="TOTAL REPORTS"
          value={mockSummary.total_reports}
          trend={mockSummary.total_reports_trend}
          icon={FileText}
          accentColor="#3b82f6"
        />

        <KPICard
          title="SIF-POTENTIAL"
          value={mockSummary.sif_precursors}
          trend={mockSummary.sif_precursors_trend}
          badgeText={`PSIF Rate: ${mockSummary.psif_rate}%`}
          badgeType="critical"
          icon={AlertTriangle}
          accentColor="#ef4444"
        />

        <KPICard
          title="HIGH CONFIDENCE"
          value={mockSummary.high_confidence_sif}
          trend={14.2}
          badgeText="Auto-Routed"
          badgeType="success"
          icon={CheckCircle2}
          accentColor="#10b981"
        />

        <KPICard
          title="NEEDS HSE REVIEW"
          value={mockSummary.needs_hse_review}
          trend={-5.1}
          badgeText="Ambiguous Bucket"
          badgeType="warning"
          icon={HelpCircle}
          accentColor="#f59e0b"
        />

        <KPICard
          title="BARRIER FAILURES"
          value={mockSummary.failed_barriers}
          trend={mockSummary.failed_barriers_trend}
          badgeText="Failure Rate: 2.5%"
          badgeType="critical"
          icon={ShieldX}
          accentColor="#ec4899"
        />

        <KPICard
          title="RECURRING PATTERNS"
          value={27}
          trend={31.0}
          badgeText="Clustered"
          badgeType="info"
          icon={Layers}
          accentColor="#8b5cf6"
        />
      </div>

      {/* 5. SIF POTENTIAL VS ACTUAL OUTCOME MATRIX */}
      <SifOutcomeMatrix />

      {/* 6. SENTINEL REASONING CHAIN VISUAL */}
      <ReasoningChainVisual />

      {/* 7. 4-BUCKET CONFIDENCE ROUTING PANEL */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl backdrop-blur-md space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-telemetry flex items-center space-x-2">
              <SlidersHorizontal className="w-4 h-4 text-blue-400" />
              <span>HSE Review Queue — 4-Bucket Confidence Routing</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated NLP triage routes reports based on SIF potential confidence and report completeness.
            </p>
          </div>
          {selectedBucketFilter && (
            <button
              onClick={() => setSelectedBucketFilter(null)}
              className="text-xs text-blue-400 hover:underline font-telemetry"
            >
              Clear Filter ({selectedBucketFilter})
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* BUCKET 1: HIGH CONFIDENCE SIF */}
          <button
            onClick={() => setSelectedBucketFilter('HIGH_CONF_SIF')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${selectedBucketFilter === 'HIGH_CONF_SIF'
                ? 'ring-2 ring-red-500 bg-red-950/40 border-red-500'
                : 'bg-slate-950/60 border-red-500/30 hover:border-red-500/60'
              }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-telemetry font-bold uppercase tracking-wider text-red-400">
                1. HIGH-CONFIDENCE SIF
              </span>
              <span className="text-xs font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/30">
                Auto-Routed
              </span>
            </div>
            <div className="text-2xl font-black text-slate-100 font-telemetry mb-1">
              48
            </div>
            <p className="text-[11px] text-slate-400 leading-tight">
              High-energy exposure + degraded critical barrier. High priority HSE intervention.
            </p>
          </button>

          {/* BUCKET 2: AMBIGUOUS / LOW CONFIDENCE */}
          <button
            onClick={() => setSelectedBucketFilter('LOW_CONF_REVIEW')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${selectedBucketFilter === 'LOW_CONF_REVIEW'
                ? 'ring-2 ring-amber-500 bg-amber-950/40 border-amber-500'
                : 'bg-slate-950/60 border-amber-500/30 hover:border-amber-500/60'
              }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-telemetry font-bold uppercase tracking-wider text-amber-400">
                2. AMBIGUOUS / LOW-CONF
              </span>
              <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                Requires Verification
              </span>
            </div>
            <div className="text-2xl font-black text-slate-100 font-telemetry mb-1">
              16
            </div>
            <p className="text-[11px] text-slate-400 leading-tight">
              Borderline SIF indicators requiring manual verification by HSE Analyst.
            </p>
          </button>

          {/* BUCKET 3: HIGH CONFIDENCE NON-SIF */}
          <button
            onClick={() => setSelectedBucketFilter('NON_SIF')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${selectedBucketFilter === 'NON_SIF'
                ? 'ring-2 ring-emerald-500 bg-emerald-950/40 border-emerald-500'
                : 'bg-slate-950/60 border-emerald-500/30 hover:border-emerald-500/60'
              }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-telemetry font-bold uppercase tracking-wider text-emerald-400">
                3. HIGH-CONF NON-SIF
              </span>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                Logged & Sampled
              </span>
            </div>
            <div className="text-2xl font-black text-slate-100 font-telemetry mb-1">
              8,914
            </div>
            <p className="text-[11px] text-slate-400 leading-tight">
              Low kinetic hazard or minor housekeeping issue. Sampled for QA verification.
            </p>
          </button>

          {/* BUCKET 4: INSUFFICIENT INFORMATION */}
          <button
            onClick={() => setSelectedBucketFilter('NEEDS_MORE_INFO')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${selectedBucketFilter === 'NEEDS_MORE_INFO'
                ? 'ring-2 ring-slate-400 bg-slate-800/40 border-slate-400'
                : 'bg-slate-950/60 border-slate-700 hover:border-slate-500'
              }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-telemetry font-bold uppercase tracking-wider text-slate-300">
                4. INSUFFICIENT DETAIL
              </span>
              <span className="text-xs font-bold text-slate-300 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                Needs Follow-up
              </span>
            </div>
            <div className="text-2xl font-black text-slate-100 font-telemetry mb-1">
              127
            </div>
            <p className="text-[11px] text-slate-400 leading-tight">
              Missing barrier or location detail. Useful safety signal for reporting quality.
            </p>
          </button>
        </div>
      </div>

      {/* 8. RECENT SAFETY REPORTS TABLE */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl backdrop-blur-md space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-telemetry flex items-center space-x-2">
              <FileText className="w-4 h-4 text-blue-400" />
              <span>Ingested Safety Observations ({filteredReports.length})</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Source observations with NLP-extracted 3-way barrier states and SIF classifications.
            </p>
          </div>
          <button
            onClick={() => navigate('/reports')}
            className="text-xs text-blue-400 hover:underline font-telemetry flex items-center space-x-1"
          >
            <span>View All Reports</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <DataTable
          columns={recentReportColumns}
          data={filteredReports}
          onRowClick={(row) => navigate(`/reports/${row.report_id}`)}
        />
      </div>

      {/* Safety Brief Modal */}
      <SafetyBriefModal isOpen={briefModalOpen} onClose={() => setBriefModalOpen(false)} siteFilter={selectedSite} />
    </div>
  );
};
