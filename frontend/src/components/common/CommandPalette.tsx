import React, { useState, useEffect } from 'react';
import { Search, FileText, Building2, Layers, ArrowRight, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { mockReports, mockClusters, mockRankings } from '../../data/mockData';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open signal handled in parent
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredReports = mockReports.filter(
    (r) =>
      r.report_id.toLowerCase().includes(query.toLowerCase()) ||
      r.site.toLowerCase().includes(query.toLowerCase()) ||
      r.hazard.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 4);

  const filteredPatterns = mockClusters.filter((c) =>
    c.pattern_summary.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 3);

  const filteredSites = mockRankings.filter((s) =>
    s.group.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 3);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/75 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-xl bg-slate-900 border border-slate-700 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800 bg-slate-950/60">
          <Search className="w-5 h-5 text-blue-400 shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search reports, hazards, sites, SIF patterns... (Press Esc to exit)"
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none font-medium"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-[60vh] overflow-y-auto p-3 space-y-4">
          {/* Reports */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              Safety Reports
            </div>
            <div className="mt-1 space-y-1">
              {filteredReports.map((r) => (
                <div
                  key={r.report_id}
                  onClick={() => {
                    navigate(`/reports/${r.report_id}`);
                    onClose();
                  }}
                  className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800/80 cursor-pointer group transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-telemetry text-xs font-bold text-blue-400 bg-blue-500/10 border border-blue-500/30 px-2 py-0.5 rounded">
                      {r.report_id}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-200 group-hover:text-white">
                        {r.site} — {r.hazard}
                      </div>
                      <div className="text-[11px] text-slate-400 line-clamp-1">
                        {r.report_text}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                </div>
              ))}
            </div>
          </div>

          {/* Patterns */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              Emerging SIF Patterns
            </div>
            <div className="mt-1 space-y-1">
              {filteredPatterns.map((p) => (
                <div
                  key={p.cluster_id}
                  onClick={() => {
                    navigate('/patterns');
                    onClose();
                  }}
                  className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800/80 cursor-pointer group transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-telemetry text-xs font-bold text-purple-400 bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded">
                      {p.cluster_id}
                    </span>
                    <span className="text-xs font-medium text-slate-200 group-hover:text-white">
                      {p.pattern_summary}
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition-colors" />
                </div>
              ))}
            </div>
          </div>

          {/* Sites */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-amber-400" />
              Industrial Sites & Assets
            </div>
            <div className="mt-1 space-y-1">
              {filteredSites.map((s) => (
                <div
                  key={s.group}
                  onClick={() => {
                    navigate('/risk-intelligence');
                    onClose();
                  }}
                  className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800/80 cursor-pointer group transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-200 group-hover:text-white">
                      {s.group}
                    </span>
                    <span className="text-[11px] font-telemetry text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                      Risk Score: {s.risk_score} ({s.risk_level})
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 transition-colors" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-500 flex justify-between">
          <span>Navigate with ↑ ↓ keys</span>
          <span>Press Esc to close</span>
        </div>
      </div>
    </div>
  );
};
