import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Sparkles, Network, CheckCircle2, ChevronRight } from 'lucide-react';
import { RiskBadge } from '../components/common/RiskBadge';
import { ActionPlanModal } from '../components/common/ActionPlanModal';
import { mockClusters, mockRecommendations, mockClusterNodes, mockClusterEdges } from '../data/mockData';
import type { Recommendation, ClusterNode, ClusterEdge } from '../types/sentinel';

export const PatternsPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [actionPlanOpen, setActionPlanOpen] = useState(false);
  const [actionCreated, setActionCreated] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const handleOpenIntervention = (patternId: string) => {
    const found = mockRecommendations.find((r) => r.pattern_id === patternId) || mockRecommendations[0];
    setSelectedRec(found);
    setActionPlanOpen(true);
  };

  const selectedNode = mockClusterNodes.find((n) => n.id === selectedNodeId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              Precursor Pattern Intelligence
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            NLP semantic clustering & precursor association network discovering recurring safety precursor patterns across observations.
          </p>
        </div>

        <span className="text-xs font-telemetry font-bold text-purple-300 bg-purple-500/10 px-3 py-1.5 rounded-lg border border-purple-500/20 self-start sm:self-auto">
          Semantic Clustering Engine Active
        </span>
      </div>

      {actionCreated && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800 text-xs text-emerald-300 font-telemetry flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Action Plan created and committed to outcome tracking module!
        </div>
      )}

      {/* 1. SEMANTIC CLUSTERING DEMO CARD ("DIFFERENT WORDING -> SAME PATTERN") */}
      <div className="bg-slate-900/90 border border-purple-500/30 rounded-xl p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-extrabold text-slate-100 uppercase tracking-wider font-telemetry">
                Semantic Clustering Demonstration: Different Wording &rarr; Same Precursor Pattern
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Demonstrating how Sentinel groups differently worded field observations into a single structured safety precursor pattern.
            </p>
          </div>
          <span className="text-[11px] font-telemetry text-purple-300 bg-purple-500/10 px-2.5 py-1 rounded border border-purple-500/20 font-bold">
            Grouped by structured similarity
          </span>
        </div>

        {/* Differently Worded Source Reports Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-telemetry text-xs">
          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center text-[10px] text-slate-500">
              <span className="font-bold text-blue-400">REPORT A (SR-10480)</span>
              <span>Rig 4</span>
            </div>
            <p className="text-slate-300 font-mono text-[11px]">
              "Worker stood below suspended pipe section."
            </p>
          </div>

          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center text-[10px] text-slate-500">
              <span className="font-bold text-blue-400">REPORT B (SR-10474)</span>
              <span>North Refinery</span>
            </div>
            <p className="text-slate-300 font-mono text-[11px]">
              "Person was positioned under lifted load."
            </p>
          </div>

          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center text-[10px] text-slate-500">
              <span className="font-bold text-blue-400">REPORT C (SR-10473)</span>
              <span>Processing Unit 4</span>
            </div>
            <p className="text-slate-300 font-mono text-[11px]">
              "Employee entered the crane load path."
            </p>
          </div>
        </div>

        {/* Sentinel Clustered Result Box */}
        <div className="p-4 bg-purple-950/20 border-2 border-purple-500/40 rounded-xl space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-telemetry text-slate-400 font-bold uppercase">
                SENTINEL CLUSTERED THESE AS:
              </span>
              <h4 className="text-sm font-black text-purple-300 font-telemetry uppercase tracking-wider">
                LINE-OF-FIRE / SUSPENDED LOAD PRECURSOR
              </h4>
            </div>
            <div className="flex items-center space-x-3 text-xs font-telemetry">
              <span>Occurrences: <strong className="text-slate-100 font-bold">27</strong></span>
              <span>Sites: <strong className="text-blue-300 font-bold">4</strong></span>
              <span>Trend: <strong className="text-red-400 font-bold">&uarr; 31%</strong></span>
            </div>
          </div>
          <div className="text-xs text-slate-300 flex items-center justify-between pt-1 border-t border-purple-800/40">
            <span>Primary Barrier: <strong className="text-amber-300">Exclusion Zone / Lifting Controls</strong></span>
            <span className="text-[11px] text-slate-400 italic">
              Grouped by structured safety-event similarity, not identical wording.
            </span>
          </div>
        </div>
      </div>

      {/* 2. PRECURSOR GRAPH / NETWORK VIEW */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <Network className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-extrabold text-slate-100 uppercase tracking-wider font-telemetry">
                Precursor Association Network Graph
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Graph representation showing explicit relationships between Activity &rarr; Energy &rarr; Barrier &rarr; Failure Mode &rarr; Site &rarr; LSR.
            </p>
          </div>
          <span className="text-[11px] font-telemetry text-cyan-300 bg-cyan-500/10 px-2.5 py-1 rounded border border-cyan-500/20 font-bold">
            Interactive Network Nodes
          </span>
        </div>

        {/* Network Graph Visualizer */}
        <div className="p-6 bg-slate-950 rounded-xl border border-slate-800 relative">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {mockClusterNodes.map((node: ClusterNode) => {
              const isSelected = selectedNodeId === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className={`p-3 rounded-lg border text-left transition-all font-telemetry cursor-pointer ${isSelected
                      ? 'bg-cyan-950/60 border-cyan-400 ring-2 ring-cyan-500/30'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-600'
                    }`}
                >
                  <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">
                    {node.type}
                  </div>
                  <div className="text-xs font-bold text-slate-100 line-clamp-2">
                    {node.label}
                  </div>
                  <div className="mt-2 text-[10px] text-cyan-400 font-bold">
                    {node.reportsCount} Reports
                  </div>
                </button>
              );
            })}
          </div>

          {/* Graph Edges / Relations List */}
          <div className="mt-4 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs font-telemetry text-slate-400">
            <span className="font-bold text-slate-300">Extracted Association Edges:</span>
            {mockClusterEdges.map((e: ClusterEdge, idx: number) => (
              <span key={idx} className="bg-slate-900 px-2.5 py-1 rounded border border-slate-800 text-[11px]">
                <strong className="text-cyan-300">{mockClusterNodes.find((n: ClusterNode) => n.id === e.source)?.label}</strong>
                <span className="mx-1.5 text-slate-500">&rarr; [{e.relation}] &rarr;</span>
                <strong className="text-amber-300">{mockClusterNodes.find((n: ClusterNode) => n.id === e.target)?.label}</strong>
              </span>
            ))}
          </div>

          {selectedNode && (
            <div className="mt-3 p-3 bg-cyan-950/30 rounded-lg border border-cyan-500/30 text-xs text-cyan-200 flex items-center justify-between">
              <span>
                Filtered by node: <strong>{selectedNode.label}</strong> ({selectedNode.reportsCount} reports associated)
              </span>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="text-cyan-400 hover:underline font-bold"
              >
                Reset Filter
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 3. PRECURSOR PATTERN CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {mockClusters.map((cluster) => (
          <div
            key={cluster.cluster_id}
            className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 space-y-4 hover:border-purple-500/40 transition-all shadow-xl"
          >
            {/* Header row */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-extrabold font-telemetry text-purple-300 bg-purple-500/10 px-3 py-1 rounded border border-purple-500/30">
                  CLUSTER #{cluster.cluster_id}
                </span>
                <span className="text-xs font-telemetry text-slate-400">
                  {cluster.pattern_type.toUpperCase().replace('_', ' ')}
                </span>
              </div>
              <RiskBadge level={cluster.risk_level} size="sm" />
            </div>

            {/* Title */}
            <h3 className="text-base font-extrabold text-slate-100">
              {cluster.pattern_summary}
            </h3>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950 border border-slate-800 font-telemetry text-xs">
              <div>
                <span className="text-slate-500 block text-[10px]">OCCURRENCES</span>
                <span className="font-black text-slate-100 text-lg">{cluster.member_count}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">GROWTH RATE</span>
                <span className="font-black text-red-400 text-lg">+{cluster.growth_rate}%</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">AFFECTED SITES</span>
                <span className="font-bold text-blue-400 text-lg">{cluster.sites.length} sites</span>
              </div>
            </div>

            {/* Why This Matters */}
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400 font-telemetry flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Why This Matters:
              </span>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/80 p-3 rounded border border-slate-800">
                {cluster.why_it_matters}
              </p>
            </div>

            {/* Actions */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
              <button
                onClick={() => navigate(`/reports/${cluster.member_report_ids[0]}`)}
                className="text-xs text-blue-400 hover:underline font-telemetry flex items-center space-x-1"
              >
                <span>View Source Reports ({cluster.member_report_ids.length})</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleOpenIntervention(cluster.cluster_id)}
                className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-telemetry text-xs font-bold transition-all shadow-md"
              >
                Create Intervention Plan
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Action Plan Modal */}
      {selectedRec && (
        <ActionPlanModal
          isOpen={actionPlanOpen}
          onClose={() => setActionPlanOpen(false)}
          recommendation={selectedRec}
          onSuccess={() => setActionCreated(true)}
        />
      )}
    </div>
  );
};
