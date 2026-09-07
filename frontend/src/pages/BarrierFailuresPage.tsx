import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldX, Grid, ChevronRight } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { mockBarrierStats, mockMatrixItems } from '../data/mockData';
import type { BarrierStat, Matrix2DItem } from '../types/sentinel';

export const BarrierFailuresPage: React.FC = () => {
  const navigate = useNavigate();

  const rareHighSif = mockMatrixItems.filter((i: Matrix2DItem) => i.recurrence === 'RARE' && i.severity === 'HIGH_SIF');
  const recurringHighSif = mockMatrixItems.filter((i: Matrix2DItem) => i.recurrence === 'RECURRING' && i.severity === 'HIGH_SIF');
  const rareLowerRisk = mockMatrixItems.filter((i: Matrix2DItem) => i.recurrence === 'RARE' && i.severity === 'LOWER_RISK');
  const recurringLowerRisk = mockMatrixItems.filter((i: Matrix2DItem) => i.recurrence === 'RECURRING' && i.severity === 'LOWER_RISK');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
            Safety Barrier Failure Intelligence
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            3-way barrier health tracking (Confirmed Effective, Degraded, Absent/Not Confirmed) and 2D Recurrence vs. Severity analytics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-telemetry font-bold text-red-400 bg-red-500/10 px-3 py-1.5 rounded-lg border border-red-500/20">
            312 Active Barrier Failures
          </span>
        </div>
      </div>

      {/* HERO STATS */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 font-telemetry">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-lg">
          <div className="text-[10px] font-bold text-slate-400 uppercase">TOTAL BARRIER FAILURES</div>
          <div className="text-2xl font-black text-slate-100 mt-1">312</div>
          <div className="text-xs text-red-400 mt-1 font-bold">+12.4% vs baseline</div>
        </div>

        <div className="p-4 rounded-xl bg-red-950/20 border border-red-900/40 shadow-lg">
          <div className="text-[10px] font-bold text-red-400 uppercase">MOST DEGRADED BARRIER</div>
          <div className="text-sm font-bold text-slate-100 mt-1 truncate">FALL PROTECTION</div>
          <div className="text-xs text-red-400 mt-1 font-bold">127 Reports (+42%)</div>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/40 shadow-lg">
          <div className="text-[10px] font-bold text-amber-400 uppercase">ENERGY ISOLATION FAILURES</div>
          <div className="text-2xl font-black text-amber-400 mt-1">91 Reports</div>
          <div className="text-xs text-amber-300 mt-1 font-bold">+18% increase across 3 sites</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-lg">
          <div className="text-[10px] font-bold text-slate-400 uppercase">UNCONFIRMED BARRIER RATE</div>
          <div className="text-2xl font-black text-blue-400 mt-1">62% of Incomplete</div>
          <div className="text-xs text-slate-400 mt-1">Absence &ne; Safety</div>
        </div>
      </div>

      {/* 2D MATRIX: SEPARATE RECURRENCE FROM SEVERITY */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <Grid className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-extrabold text-slate-100 uppercase tracking-wider font-telemetry">
                2D Matrix: Recurrence vs. Severity Analysis
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Domain Principle: <strong className="text-slate-200">Recurrence and severity are separate dimensions. A rare event can still be critical.</strong>
            </p>
          </div>
          <span className="text-[11px] font-telemetry text-amber-300 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/20 self-start sm:self-auto font-bold">
            2D Risk Separation
          </span>
        </div>

        {/* 2D Grid Representation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* QUADRANT 1: RARE + HIGH SEVERITY */}
          <div className="p-4 rounded-xl bg-red-950/20 border-2 border-red-500/50 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-red-500/30">
              <span className="text-xs font-telemetry font-extrabold text-red-400 uppercase tracking-wider">
                RARE + HIGH SIF SEVERITY
              </span>
              <span className="text-[10px] font-telemetry bg-red-500/20 text-red-300 px-2 py-0.5 rounded font-bold">
                CRITICAL FOCUS
              </span>
            </div>
            <p className="text-[11px] text-slate-300 italic">
              Low reporting frequency but extreme fatality risk upon failure. Never ignore due to low count!
            </p>
            <div className="space-y-2 font-telemetry text-xs">
              {rareHighSif.map((item: Matrix2DItem) => (
                <div key={item.id} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-100">{item.pattern}</div>
                    <div className="text-[10px] text-slate-400">Barrier: {item.barrier} • LSR: {item.lsr}</div>
                  </div>
                  <span className="font-black text-red-400 text-sm">{item.reportCount} reports</span>
                </div>
              ))}
            </div>
          </div>

          {/* QUADRANT 2: RECURRING + HIGH SEVERITY */}
          <div className="p-4 rounded-xl bg-purple-950/20 border-2 border-purple-500/50 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-purple-500/30">
              <span className="text-xs font-telemetry font-extrabold text-purple-300 uppercase tracking-wider">
                RECURRING + HIGH SIF SEVERITY
              </span>
              <span className="text-[10px] font-telemetry bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded font-bold">
                SYSTEMIC URGENT
              </span>
            </div>
            <p className="text-[11px] text-slate-300 italic">
              Systemic recurring pattern with high fatality potential. Mandates immediate engineering intervention.
            </p>
            <div className="space-y-2 font-telemetry text-xs">
              {recurringHighSif.map((item: Matrix2DItem) => (
                <div key={item.id} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-100">{item.pattern}</div>
                    <div className="text-[10px] text-slate-400">Barrier: {item.barrier} • LSR: {item.lsr}</div>
                  </div>
                  <span className="font-black text-purple-300 text-sm">{item.reportCount} reports</span>
                </div>
              ))}
            </div>
          </div>

          {/* QUADRANT 3: RARE + LOWER RISK */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <span className="text-xs font-telemetry font-bold text-slate-400 uppercase tracking-wider">
                RARE + LOWER RISK
              </span>
              <span className="text-[10px] font-telemetry bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-bold">
                ROUTINE LOG
              </span>
            </div>
            <div className="space-y-2 font-telemetry text-xs">
              {rareLowerRisk.map((item: Matrix2DItem) => (
                <div key={item.id} className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-300">{item.pattern}</div>
                    <div className="text-[10px] text-slate-500">Barrier: {item.barrier}</div>
                  </div>
                  <span className="font-bold text-slate-400 text-sm">{item.reportCount} reports</span>
                </div>
              ))}
            </div>
          </div>

          {/* QUADRANT 4: RECURRING + LOWER RISK */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <span className="text-xs font-telemetry font-bold text-blue-400 uppercase tracking-wider">
                RECURRING + LOWER RISK
              </span>
              <span className="text-[10px] font-telemetry bg-blue-500/10 text-blue-300 px-2 py-0.5 rounded font-bold">
                OPERATIONAL WEAR
              </span>
            </div>
            <div className="space-y-2 font-telemetry text-xs">
              {recurringLowerRisk.map((item: Matrix2DItem) => (
                <div key={item.id} className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-300">{item.pattern}</div>
                    <div className="text-[10px] text-slate-500">Barrier: {item.barrier}</div>
                  </div>
                  <span className="font-bold text-blue-400 text-sm">{item.reportCount} reports</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* RANKED BARRIER FAILURE INTELLIGENCE LIST */}
      <div className="rounded-xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-2xl">
        <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-extrabold uppercase tracking-wider text-slate-100 font-telemetry">
              Most Frequently Degraded Safety Barriers
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Ranked breakdown by occurrences, trend, affected sites, LSR mapping & 3-way barrier status.
            </p>
          </div>
        </div>

        <div className="divide-y divide-slate-800 font-telemetry">
          {mockBarrierStats.map((b: BarrierStat) => (
            <div
              key={b.barrier}
              onClick={() => navigate(`/reports?barrier=${encodeURIComponent(b.barrier)}`)}
              className="p-5 hover:bg-slate-800/60 cursor-pointer transition-colors space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-3">
                  <span className="p-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
                    <ShieldX className="w-5 h-5" />
                  </span>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="text-base font-extrabold text-slate-100 tracking-wide">
                        {b.barrier}
                      </h4>
                      <RiskBadge level={b.severity} size="sm" />
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {b.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-xl font-black text-slate-100">{b.failures}</div>
                    <div className="text-[10px] text-slate-500 uppercase font-bold">TOTAL REPORTS</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-base font-bold ${b.trend_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {b.trend_pct > 0 ? `+${b.trend_pct}%` : `${b.trend_pct}%`}
                    </div>
                    <div className="text-[10px] text-slate-500 uppercase font-bold">30D TREND</div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-500" />
                </div>
              </div>

              {/* Breakdown detail bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-xs">
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">AFFECTED SITES</span>
                  <span className="font-bold text-blue-400">{b.sites_affected} Sites</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">PRIMARY LSR MAPPING</span>
                  <span className="font-bold text-emerald-400">{b.barrier.split(' ')[0]} Controls</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">3-WAY BARRIER STATUS</span>
                  <span className="font-bold text-amber-300">
                    {b.state_3way === 'ABSENT_NOT_CONFIRMED' ? 'ABSENT / UNCONFIRMED' : 'DEGRADED'}
                  </span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">LAST DETECTED</span>
                  <span className="font-bold text-slate-300">{new Date(b.last_detected).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
