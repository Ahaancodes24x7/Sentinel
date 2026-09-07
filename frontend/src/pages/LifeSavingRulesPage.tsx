import React from 'react';
import { CheckSquare } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { mockLifeSavingRules } from '../data/mockData';

export const LifeSavingRulesPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <CheckSquare className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              IOGP Life-Saving Rules Performance
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time compliance tracking across standard Oil & Gas Life-Saving Rules.
          </p>
        </div>
        <span className="text-xs font-telemetry font-bold text-blue-400 bg-blue-500/10 px-3 py-1.5 rounded-lg border border-blue-500/20">
          IOGP Industry Standard
        </span>
      </div>

      {/* Grid of Rules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {mockLifeSavingRules.map((rule) => (
          <div
            key={rule.id}
            className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3 shadow-xl hover:border-slate-700 transition-all"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
                {rule.name}
              </span>
              <RiskBadge level={rule.risk_level} size="sm" />
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-950 p-2.5 rounded border border-slate-800">
              {rule.description}
            </p>

            <div className="space-y-1 font-telemetry">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Compliance Rate:</span>
                <span className="font-bold text-slate-100">{rule.compliance_pct}% ({rule.violations_count} violations)</span>
              </div>
              <div className="w-full h-3 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${rule.compliance_pct < 80 ? 'bg-red-500' : rule.compliance_pct < 90 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                  style={{ width: `${rule.compliance_pct}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
