import React from 'react';
import { History, Lock } from 'lucide-react';
import { DataTable } from '../components/common/DataTable';
import type { Column } from '../components/common/DataTable';
import { mockAuditLogs } from '../data/mockData';
import type { AuditLogEntry } from '../types/sentinel';

export const AuditLogPage: React.FC = () => {
  const columns: Column<AuditLogEntry>[] = [
    {
      header: 'Audit Hash ID',
      accessorKey: 'id',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry font-bold text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-mono text-[11px]">
          {row.id}
        </span>
      ),
    },
    {
      header: 'Timestamp',
      accessorKey: 'timestamp',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry text-slate-400 text-[11px]">
          {new Date(row.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      header: 'Report ID',
      accessorKey: 'entity_id',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry font-bold text-blue-400">
          {row.entity_id}
        </span>
      ),
    },
    {
      header: 'Model Version',
      accessorKey: 'model_version',
      cell: (row) => (
        <span className="font-telemetry text-purple-300 font-semibold text-xs">
          {row.model_version || 'Sentinel-NLP v0.4'}
        </span>
      ),
    },
    {
      header: 'SIF Classification & Confidence',
      accessorKey: 'sif_classification',
      cell: (row) => (
        <div className="font-telemetry text-xs">
          <span className="font-bold text-red-400">SIF: {row.sif_classification || 'HIGH'}</span>
          <span className="text-emerald-400 font-bold ml-2">({Math.round((row.confidence || 0.94) * 100)}%)</span>
        </div>
      ),
    },
    {
      header: 'LSR Mapping',
      accessorKey: 'lsr_mapping',
      cell: (row) => (
        <span className="font-telemetry text-slate-300 font-medium text-xs">
          {row.lsr_mapping || 'Working at Height'}
        </span>
      ),
    },
    {
      header: 'Reviewer Action',
      accessorKey: 'action',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30 text-xs">
          {row.action}
        </span>
      ),
    },
    {
      header: 'Actor / User',
      accessorKey: 'actor',
      sortable: true,
      cell: (row) => (
        <span className="font-telemetry text-slate-300 text-xs">
          {row.actor}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6 font-telemetry">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 font-sans">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <History className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              Immutable Governance Audit Trail
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-evident log recording all automated NLP classifications, LSR mappings, and human HSE reviewer actions.
          </p>
        </div>

        <span className="text-xs font-telemetry font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20 flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5" />
          Cryptographic Audit Enabled
        </span>
      </div>

      <DataTable
        columns={columns}
        data={mockAuditLogs}
        searchPlaceholder="Search audit records by report ID, model version, actor..."
        pageSize={10}
      />
    </div>
  );
};
