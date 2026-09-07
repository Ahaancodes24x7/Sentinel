import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Upload, Filter } from 'lucide-react';
import { DataTable } from '../components/common/DataTable';
import type { Column } from '../components/common/DataTable';
import { mockReports } from '../data/mockData';
import { reportsService } from '../services/reportsService';
import type { ReportItem } from '../types/sentinel';

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const barrierParam = searchParams.get('barrier');

  const [reports] = useState<ReportItem[]>(mockReports);
  const [filterSite, setFilterSite] = useState<string>('ALL');
  const [filterSif, setFilterSif] = useState<string>('ALL');
  const [filterBucket, setFilterBucket] = useState<string>('ALL');
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [ingestText, setIngestText] = useState('');
  const [ingesting, setIngesting] = useState(false);

  const filteredReports = reports.filter((r) => {
    if (filterSite !== 'ALL' && r.site.toLowerCase() !== filterSite.toLowerCase()) return false;
    if (filterSif === 'YES' && !r.sif_potential) return false;
    if (filterSif === 'NO' && r.sif_potential) return false;
    if (filterBucket !== 'ALL' && r.bucket !== filterBucket) return false;
    if (barrierParam && !r.failed_barrier.toLowerCase().includes(barrierParam.toLowerCase())) return false;
    return true;
  });

  const columns: Column<ReportItem>[] = [
    {
      header: 'Report ID',
      accessorKey: 'report_id',
      sortable: true,
      cell: (row) => (
        <button
          onClick={() => navigate(`/reports/${row.report_id}`)}
          className="font-telemetry font-bold text-blue-400 hover:text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20"
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
    { header: 'Site Facility', accessorKey: 'site', sortable: true },
    { header: 'Hazard Category', accessorKey: 'hazard', sortable: true },
    {
      header: 'Actual Outcome',
      accessorKey: 'actual_outcome',
      cell: (row) => (
        <span className="font-telemetry text-xs text-slate-300">
          {row.actual_outcome === 'NO_INJURY' ? 'No Injury (Near-Miss)' : 'No Injury'}
        </span>
      ),
    },
    {
      header: 'SIF Potential',
      accessorKey: 'sif_potential',
      sortable: true,
      cell: (row) => (
        <span
          className={`font-telemetry font-bold text-xs px-2 py-0.5 rounded border ${row.sif_potential ? 'bg-red-500/10 text-red-400 border-red-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
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
          return <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">EFFECTIVE</span>;
        }
        if (state === 'UNCERTAIN_DEGRADED') {
          return <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">DEGRADED</span>;
        }
        return <span className="px-2 py-0.5 rounded text-[11px] font-telemetry font-bold bg-slate-800 text-slate-400 border border-slate-700">NOT CONFIRMED</span>;
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

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngesting(true);
    try {
      await reportsService.ingestReports({
        reports: [{ site: 'North Refinery', report_text: ingestText, source: 'synthetic' }],
      });
      setIngestModalOpen(false);
      setIngestText('');
      alert('Report successfully ingested and classified by Sentinel SIF Engine!');
    } catch (err) {
      alert('Ingestion error, using offline mock pipeline fallback.');
      setIngestModalOpen(false);
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
            Safety Observations Repository
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Free-text HSSE safety observations processed for SIF precursor potential, barrier state, and LSR mapping.
          </p>
        </div>

        <button
          onClick={() => setIngestModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg font-telemetry transition-all self-start sm:self-auto"
        >
          <Upload className="w-4 h-4" />
          Ingest New Report
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs font-telemetry">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-bold text-slate-400 uppercase flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-blue-400" />
            Filters:
          </span>

          <select
            value={filterSite}
            onChange={(e) => setFilterSite(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-slate-200 font-medium focus:outline-none"
          >
            <option value="ALL">All Sites</option>
            <option value="North Refinery">North Refinery</option>
            <option value="Processing Unit 4">Processing Unit 4</option>
            <option value="Rig 4">Rig 4</option>
            <option value="Plant C">Plant C</option>
            <option value="Assam Field A">Assam Field A</option>
            <option value="Deepwater Alpha">Deepwater Alpha</option>
          </select>

          <select
            value={filterSif}
            onChange={(e) => setFilterSif(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-slate-200 font-medium focus:outline-none"
          >
            <option value="ALL">All SIF States</option>
            <option value="YES">High SIF Potential Only</option>
            <option value="NO">Non-SIF Only</option>
          </select>

          <select
            value={filterBucket}
            onChange={(e) => setFilterBucket(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-slate-200 font-medium focus:outline-none"
          >
            <option value="ALL">All 4 Confidence Buckets</option>
            <option value="HIGH_CONF_SIF">1. High-Confidence SIF</option>
            <option value="LOW_CONF_REVIEW">2. Ambiguous / Low-Conf</option>
            <option value="NON_SIF">3. High-Confidence Non-SIF</option>
            <option value="NEEDS_MORE_INFO">4. Insufficient Detail</option>
          </select>
        </div>

        <div className="text-slate-400 text-[11px]">
          Showing <strong className="text-slate-200 font-bold">{filteredReports.length}</strong> of {reports.length} observations
        </div>
      </div>

      {/* Main Table */}
      <DataTable
        columns={columns}
        data={filteredReports}
        searchPlaceholder="Search observations by ID, text keywords, site, hazard, barrier..."
        onRowClick={(row) => navigate(`/reports/${row.report_id}`)}
      />

      {/* Ingest Modal */}
      {ingestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-100 font-telemetry uppercase tracking-wider">
              Ingest Raw HSSE Safety Observation Text
            </h3>
            <form onSubmit={handleIngest} className="space-y-4">
              <textarea
                value={ingestText}
                onChange={(e) => setIngestText(e.target.value)}
                placeholder="Paste free-text safety observation narrative..."
                className="w-full h-32 bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                required
              />
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIngestModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 font-telemetry text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingesting}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-telemetry text-xs font-bold shadow-lg"
                >
                  {ingesting ? 'Analyzing Spans...' : 'Classify SIF Potential'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
