import React from 'react';
import { AlertCircle, ShieldAlert, CheckCircle2, Info } from 'lucide-react';

interface SifOutcomeMatrixProps {
  className?: string;
}

export const SifOutcomeMatrix: React.FC<SifOutcomeMatrixProps> = ({ className = '' }) => {
  return (
    <div className={`bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl backdrop-blur-md ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-telemetry">
              SIF Potential vs. Actual Outcome Matrix
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Core Safety Principle: <strong className="text-slate-200">Outcome severity and fatal potential are independent dimensions.</strong>
          </p>
        </div>
        <div className="flex items-center space-x-1 text-[11px] font-telemetry text-amber-300 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/20 self-start sm:self-auto">
          <Info className="w-3.5 h-3.5 mr-1" />
          <span>High Energy + Failed Barrier = High SIF</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left text-slate-500 font-telemetry uppercase text-[10px]">
                Actual Outcome \ SIF Potential
              </th>
              <th className="p-2 text-center text-emerald-400 font-telemetry uppercase text-[10px]">
                Low SIF Potential
              </th>
              <th className="p-2 text-center text-blue-400 font-telemetry uppercase text-[10px]">
                Medium SIF Potential
              </th>
              <th className="p-2 text-center text-amber-400 font-telemetry uppercase text-[10px]">
                High SIF Potential
              </th>
              <th className="p-2 text-center text-red-400 font-telemetry uppercase text-[10px]">
                Critical SIF Potential
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-telemetry">
            {/* ROW 1: NO INJURY */}
            <tr className="hover:bg-slate-800/30">
              <td className="p-2.5 font-bold text-slate-200 bg-slate-950/40 border-r border-slate-800">
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>No Injury (Near-Miss)</span>
                </div>
              </td>
              <td className="p-2.5 text-center text-slate-400 bg-slate-900/40">
                8,914
              </td>
              <td className="p-2.5 text-center text-slate-300 bg-slate-900/40">
                127
              </td>
              {/* HIGHLIGHT CELL: NO INJURY + HIGH SIF */}
              <td className="p-2.5 text-center font-bold text-amber-300 bg-amber-950/30 border-2 border-amber-500/50 shadow-inner rounded relative">
                <div className="flex flex-col items-center">
                  <span className="text-sm font-extrabold text-amber-400">48</span>
                  <span className="text-[9px] text-amber-300 uppercase tracking-tighter mt-0.5">
                    High Energy Precursors
                  </span>
                </div>
              </td>
              {/* HIGHLIGHT CELL: NO INJURY + CRITICAL SIF */}
              <td className="p-2.5 text-center font-bold text-red-300 bg-red-950/40 border-2 border-red-500/60 shadow-inner rounded relative">
                <div className="flex flex-col items-center">
                  <span className="text-sm font-extrabold text-red-400">16</span>
                  <span className="text-[9px] text-red-300 uppercase tracking-tighter mt-0.5">
                    Critical Precursors
                  </span>
                </div>
              </td>
            </tr>

            {/* ROW 2: MINOR INJURY */}
            <tr className="hover:bg-slate-800/30">
              <td className="p-2.5 font-bold text-slate-300 bg-slate-950/40 border-r border-slate-800">
                <div className="flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Minor Injury (First Aid)</span>
                </div>
              </td>
              <td className="p-2.5 text-center text-slate-400">1,240</td>
              <td className="p-2.5 text-center text-slate-300">84</td>
              <td className="p-2.5 text-center text-amber-400 font-semibold">12</td>
              <td className="p-2.5 text-center text-red-400 font-semibold">3</td>
            </tr>

            {/* ROW 3: SERIOUS INJURY */}
            <tr className="hover:bg-slate-800/30">
              <td className="p-2.5 font-bold text-slate-300 bg-slate-950/40 border-r border-slate-800">
                <div className="flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  <span>Serious Injury / LTI</span>
                </div>
              </td>
              <td className="p-2.5 text-center text-slate-500">12</td>
              <td className="p-2.5 text-center text-slate-400">8</td>
              <td className="p-2.5 text-center text-amber-400 font-bold">14</td>
              <td className="p-2.5 text-center text-red-400 font-bold">5</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-3 p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span>
            Highlighted Box: <strong>64 Near-Miss reports had zero injury</strong> but contained high-energy exposure & missing barriers.
          </span>
        </div>
        <span className="font-telemetry text-[11px] text-cyan-400">
          DEKRA SIF & EEI SCL Methodology
        </span>
      </div>
    </div>
  );
};
