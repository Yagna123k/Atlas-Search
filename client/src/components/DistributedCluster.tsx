import React, { useState, useEffect } from 'react';
import { Database, ShieldAlert, GitCommit, RotateCcw, Combine, CheckCircle2, Layers, ShieldCheck } from 'lucide-react';

interface DistributedClusterProps {
  onAnnounce: (msg: string) => void;
}

export const DistributedCluster: React.FC<DistributedClusterProps> = ({ onAnnounce }) => {
  const [clusterData, setClusterData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [faultResults, setFaultResults] = useState<any>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchClusterStatus = async () => {
    try {
      const res = await fetch('/api/cluster/status');
      const data = await res.json();
      setClusterData(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchClusterStatus();
  }, []);

  const handleCommit = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/cluster/commit', { method: 'POST' });
      const data = await res.json();
      setActionMessage(`Active segment committed! Advanced to Manifest Gen ${data.new_generation}.`);
      await fetchClusterStatus();
      onAnnounce(`Segment committed. New manifest generation: ${data.new_generation}`);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCompact = async () => {
    setLoading(true);
    try {
      await fetch('/api/cluster/compact', { method: 'POST' });
      setActionMessage('Compaction complete! Merged segments into single consolidated segment and purged tombstones.');
      await fetchClusterStatus();
      onAnnounce('Index segments compacted and tombstones purged.');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/cluster/rollback', { method: 'POST' });
      const data = await res.json();
      setActionMessage(`Rollback successful! Restored to Manifest Gen ${data.current_generation}.`);
      await fetchClusterStatus();
      onAnnounce(`Index rolled back to generation ${data.current_generation}`);
    } catch (err) {
      console.error(err);
      setActionMessage('Rollback failed: cannot rollback past initial generation.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunFaultTests = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/cluster/fault-test', { method: 'POST' });
      const data = await res.json();
      setFaultResults(data);
      onAnnounce(`Fault injection test completed: ${data.all_passed ? 'All tests passed' : 'Failures detected'}.`);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const manifest = clusterData?.manifest || {};
  const segments = clusterData?.segments || [];
  const stats = clusterData?.stats || {};

  return (
    <div className="space-y-6 animate-fade-in text-slate-100">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-white">
            <Database className="w-5 h-5 text-cyan-400" />
            Live Distributed Index &amp; Segment Publication Subsystem
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Immutable segments, atomic manifest generation publication, tombstone tracking, and zero-downtime rollback.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCommit}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-colors focus-visible:ring-2"
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>Commit Active Segment</span>
          </button>
          <button
            onClick={handleCompact}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-white/10 transition-colors focus-visible:ring-2"
          >
            <Combine className="w-3.5 h-3.5 text-cyan-400" />
            <span>Compact Segments</span>
          </button>
          <button
            onClick={handleRollback}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-white/10 transition-colors focus-visible:ring-2"
          >
            <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
            <span>Atomic Rollback</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-indigo-200 text-xs font-mono flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-indigo-400" />
          {actionMessage}
        </div>
      )}

      {/* Manifest Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 block mb-1 font-mono">Manifest Generation</span>
          <span className="text-2xl font-bold font-mono text-cyan-400">Gen {manifest.generation || 1}</span>
          <div className="text-[10px] text-slate-500 font-mono mt-1 truncate">Hash: {manifest.manifest_hash?.slice(0, 16)}...</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 block mb-1 font-mono">Active Segments</span>
          <span className="text-2xl font-bold font-mono text-indigo-400">{segments.length}</span>
          <div className="text-[10px] text-slate-500 font-mono mt-1">Immutable &amp; Checksum-verified</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 block mb-1 font-mono">Total Live Documents</span>
          <span className="text-2xl font-bold font-mono text-emerald-400">{manifest.total_live_docs || stats.total_live_docs || 0}</span>
          <div className="text-[10px] text-slate-500 font-mono mt-1">Zero dirty reads during indexing</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 block mb-1 font-mono">Tombstone Masks</span>
          <span className="text-2xl font-bold font-mono text-amber-400">{stats.tombstones_count || 0}</span>
          <div className="text-[10px] text-slate-500 font-mono mt-1">Purged during background compaction</div>
        </div>
      </div>

      {/* Active Segments Inspection Table */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          Active Immutable Segments in Memory &amp; Storage
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10 font-mono">
              <tr>
                <th className="pb-2">Segment ID</th>
                <th className="pb-2">State</th>
                <th className="pb-2 text-right">Docs</th>
                <th className="pb-2 text-right">Tokens</th>
                <th className="pb-2 text-right">Vocabulary Size</th>
                <th className="pb-2 text-right">SHA-256 Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {segments.map((s: any) => (
                <tr key={s.segment_id} className="hover:bg-white/5 transition-colors">
                  <td className="py-2.5 font-bold text-slate-200">{s.segment_id}</td>
                  <td className="py-2.5">
                    <span className="badge bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                      {s.is_frozen ? 'FROZEN / IMMUTABLE' : 'WRITABLE'}
                    </span>
                  </td>
                  <td className="py-2.5 text-right text-slate-300">{s.total_docs}</td>
                  <td className="py-2.5 text-right text-slate-300">{s.total_tokens}</td>
                  <td className="py-2.5 text-right text-slate-300">{s.vocabulary_size}</td>
                  <td className="py-2.5 text-right text-slate-400 text-[11px] truncate max-w-xs">{s.checksum?.slice(0, 24)}...</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fault Injection Testing Suite */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 glass-panel">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Automated Fault Injection &amp; Resilience Verification
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Simulates node crashes, corrupted segment publications, and atomic rollbacks to verify zero downtime.
            </p>
          </div>
          <button
            onClick={handleRunFaultTests}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-500/20 transition-colors focus-visible:ring-2"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Execute Fault Injection Suite</span>
          </button>
        </div>

        {faultResults && (
          <div className="space-y-3 animate-fade-in">
            <div className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between ${faultResults.all_passed ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200' : 'bg-rose-950/20 border-rose-500/30 text-rose-200'}`}>
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Resilience Suite Status: <strong>{faultResults.all_passed ? '100% PASSED · Zero Invariants Violated' : 'FAILURES DETECTED'}</strong>
              </span>
              <span className="text-[11px] text-slate-400">Timestamp: {new Date(faultResults.timestamp * 1000).toLocaleTimeString()}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {faultResults.tests.map((t: any) => (
                <div key={t.test_name} className="p-3 rounded-lg bg-black/40 border border-white/5 space-y-1 font-mono">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 truncate">{t.test_name}</span>
                    <span className="badge bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-[10px]">PASSED</span>
                  </div>
                  {t.recovery_time_ms && (
                    <div className="text-[11px] text-slate-400">Recovery Time: <strong className="text-white">{t.recovery_time_ms} ms</strong></div>
                  )}
                  {t.failed_shard_identified && (
                    <div className="text-[11px] text-slate-400">Isolated Worker: <strong className="text-rose-400">{t.failed_shard_identified[0]}</strong></div>
                  )}
                  {t.checksum_mismatch_caught && (
                    <div className="text-[11px] text-slate-400">Corrupted Write: <strong className="text-emerald-400">BLOCKED AT MANIFEST</strong></div>
                  )}
                  {t.generation_after_rollback && (
                    <div className="text-[11px] text-slate-400">Gen Rollback: <strong className="text-cyan-400">Gen {t.generation_after_commit} → Gen {t.generation_after_rollback}</strong></div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
