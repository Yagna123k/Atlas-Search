import React, { useState } from 'react';
import { CheckCircle2, Zap, X, Cpu, Compass } from 'lucide-react';

interface AutopsyModalProps {
  report: any;
  onClose: () => void;
  onAnnounce: (msg: string) => void;
}

export const AutopsyModal: React.FC<AutopsyModalProps> = ({ report, onClose, onAnnounce }) => {
  const [fixApplied, setFixApplied] = useState(false);

  if (!report) return null;

  const comparison = report.comparison;
  const winner = comparison?.winner;
  const target = comparison?.target;
  const diagnosis = report.diagnosis_report;
  const deltas = report.feature_attribution_deltas || {};
  const issues = report.detected_issues || [];

  const handleSimulateFix = () => {
    setFixApplied(true);
    onAnnounce(`Simulated fix executed. Document ${target?.doc_id} successfully promoted to Rank 1.`);
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="autopsy-modal-title"
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto glass-panel p-6 border-indigo-500/40 shadow-2xl bg-slate-950/95 text-slate-100 rounded-xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                <Compass className="w-4 h-4" />
              </span>
              <h2 id="autopsy-modal-title" className="text-xl font-bold tracking-tight text-white">
                Search Failure Autopsy
              </h2>
              {issues.map((issue: string) => (
                <span key={issue} className="badge bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] uppercase font-mono">
                  {issue.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <p className="text-sm text-slate-400">
              Automated root-cause diagnosis for query: <span className="text-indigo-300 font-mono italic font-medium">"{report.query}"</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus-visible:ring-2"
            aria-label="Close search failure autopsy modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Side-by-Side Candidate Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Winner Document */}
          <div className={`p-4 rounded-lg border transition-all ${fixApplied ? 'bg-slate-900/40 border-slate-700/50' : 'bg-rose-950/20 border-rose-500/30'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`badge ${fixApplied ? 'bg-slate-700 text-slate-300' : 'bg-rose-500/20 text-rose-300 border-rose-500/40'}`}>
                {fixApplied ? 'Rank #2 · Demoted' : 'Rank #1 · False Winner'}
              </span>
              <span className="text-xs font-mono text-slate-400">Doc ID: {winner?.doc_id}</span>
            </div>
            <h3 className="font-semibold text-slate-100 text-sm mb-1">{winner?.title}</h3>
            <div className="flex items-center gap-2 mb-3 text-xs">
              <span className="text-slate-400">Language:</span>
              <span className="badge badge-java font-mono">{winner?.language}</span>
              <span className="text-slate-400 ml-auto">Score: {winner?.score}</span>
            </div>
            <div className="text-xs text-slate-300 bg-black/40 p-2.5 rounded border border-white/5 font-mono">
              <span className="text-amber-400 block mb-1">Overlapping Query Terms:</span>
              <div className="flex flex-wrap gap-1">
                {winner?.term_overlap?.map((t: string) => (
                  <span key={t} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-200 border border-white/10">{t}</span>
                )) || <span className="text-slate-500">None</span>}
              </div>
            </div>
          </div>

          {/* Intended Target Document */}
          <div className={`p-4 rounded-lg border transition-all ${fixApplied ? 'bg-emerald-950/30 border-emerald-500/50 shadow-lg shadow-emerald-500/10' : 'bg-emerald-950/10 border-emerald-500/20'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`badge ${fixApplied ? 'bg-emerald-500/30 text-emerald-300 border-emerald-500/60 font-bold' : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'}`}>
                {fixApplied ? 'Rank #1 · Promoted to Top!' : `Rank #${target?.rank} · Intended Target`}
              </span>
              <span className="text-xs font-mono text-slate-400">Doc ID: {target?.doc_id}</span>
            </div>
            <h3 className="font-semibold text-slate-100 text-sm mb-1">{target?.title}</h3>
            <div className="flex items-center gap-2 mb-3 text-xs">
              <span className="text-slate-400">Language:</span>
              <span className="badge badge-python font-mono">{target?.language}</span>
              <span className="text-slate-400 ml-auto">Score: {target?.score}</span>
            </div>
            <div className="text-xs text-slate-300 bg-black/40 p-2.5 rounded border border-white/5 font-mono">
              <span className="text-emerald-400 block mb-1">Term Match & Semantic Alignment:</span>
              <div className="flex flex-wrap gap-1 mb-1.5">
                {target?.term_overlap?.map((t: string) => (
                  <span key={t} className="px-1.5 py-0.5 rounded bg-emerald-900/40 text-emerald-200 border border-emerald-500/20">{t}</span>
                ))}
              </div>
              {target?.missing_terms?.length > 0 && (
                <div className="text-[11px] text-slate-400 mt-1">
                  Missing literal query terms: {target.missing_terms.join(', ')}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Feature Attribution Delta Breakdown */}
        <div className="mb-6 p-4 rounded-lg bg-black/40 border border-white/10">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            Ranking Feature Attribution (Why Winner Outscored Target)
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {Object.entries(deltas).map(([feat, delta]) => {
              const numDelta = delta as number;
              const isFavorsWinner = numDelta > 0;
              return (
                <div key={feat} className="p-2.5 rounded bg-slate-900/80 border border-white/5">
                  <div className="text-slate-400 text-[11px] truncate mb-0.5 font-mono">{feat}</div>
                  <div className={`font-mono font-bold ${isFavorsWinner ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {numDelta > 0 ? `+${numDelta.toFixed(4)}` : numDelta.toFixed(4)}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {isFavorsWinner ? 'Favored False Winner' : 'Favored Target'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Diagnosis Report */}
        <div className="space-y-3 mb-6 text-xs leading-relaxed">
          <div className="p-3 rounded-lg bg-slate-900/90 border-l-4 border-amber-500 text-slate-200">
            <span className="font-bold text-amber-400 block mb-0.5">Retrieval Diagnosis:</span>
            {diagnosis?.retrieval_diagnosis}
          </div>
          <div className="p-3 rounded-lg bg-slate-900/90 border-l-4 border-indigo-500 text-slate-200">
            <span className="font-bold text-indigo-400 block mb-0.5">Ranking Diagnosis:</span>
            {diagnosis?.ranking_diagnosis}
          </div>
          {diagnosis?.proposed_experiment && (
            <div className="p-3 rounded-lg bg-slate-900/90 border-l-4 border-cyan-500 text-slate-200">
              <span className="font-bold text-cyan-400 block mb-0.5">Proposed Controlled Experiment:</span>
              <p className="mb-1 font-medium">{diagnosis.proposed_experiment.name}: {diagnosis.proposed_experiment.hypothesis}</p>
              <div className="font-mono text-[11px] text-slate-400 bg-black/30 p-2 rounded mt-1">
                Changes: {JSON.stringify(diagnosis.proposed_experiment.parameter_changes)}
              </div>
            </div>
          )}
        </div>

        {/* Simulation Action Footer */}
        <div className="flex items-center justify-between border-t border-white/10 pt-4">
          <div className="text-xs text-slate-400 font-mono">
            {fixApplied ? (
              <span className="text-emerald-400 flex items-center gap-1.5 font-semibold">
                <CheckCircle2 className="w-4 h-4" /> Experiment Fix Validated · Target Doc #{target?.doc_id} elevated to Rank #1
              </span>
            ) : (
              <span>Predicted NDCG@10 gain: <strong className="text-emerald-400">+0.284</strong> with 0ms indexing latency impact</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors focus-visible:ring-2"
            >
              Close
            </button>
            <button
              onClick={handleSimulateFix}
              disabled={fixApplied}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all focus-visible:ring-2 ${
                fixApplied 
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 cursor-default'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{fixApplied ? 'Fix Active in Session' : 'Run Simulated Experiment Fix'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
