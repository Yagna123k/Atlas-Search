import React, { useState, useEffect, useRef } from 'react';
import { Search, Compass, AlertTriangle, ArrowUpDown, Clock } from 'lucide-react';

interface SearchInterfaceProps {
  onOpenAutopsy: (query: string, targetDocId?: number, winnerRank?: number) => void;
  onAnnounce: (msg: string) => void;
}

export const SearchInterface: React.FC<SearchInterfaceProps> = ({ onOpenAutopsy, onAnnounce }) => {
  const [query, setQuery] = useState('How do I reduce memory usage in a Python application?');
  const [mode, setMode] = useState('hybrid_ltr');
  const [results, setResults] = useState<any[]>([]);
  const [trace, setTrace] = useState<any>(null);
  const [autopsyPreview, setAutopsyPreview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const sampleQueries = [
    { label: "Memory Failure (Python vs JVM)", q: "How do I reduce memory usage in a Python application?" },
    { label: "Paraphrased RAM Query", q: "investigate high RAM consumption in Python scripts" },
    { label: "Distributed Consensus", q: "Distributed consensus algorithms and leader election" },
    { label: "Postings Compression", q: "Fast inverted index compression variable-byte and postings lists" },
    { label: "Python 3.13 Freshness", q: "recent Python performance updates and free threading" }
  ];

  const handleSearch = async (searchQuery: string = query, searchMode: string = mode) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, mode: searchMode, top_k: 15 })
      });
      const data = await res.json();
      setResults(data.results || []);
      setTrace(data.trace);
      setAutopsyPreview(data.autopsy_preview);
      setSelectedIndex(-1);

      const count = data.results?.length || 0;
      const latency = data.trace?.total_latency_ms || 0;
      onAnnounce(`Found ${count} search results in ${latency} ms for ${searchQuery}.`);
    } catch (err) {
      console.error(err);
      onAnnounce("Search request failed. Please check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch(query, mode);
  }, [mode]);

  // Keyboard navigation listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus search input on '/' or 'Ctrl+K'
      if ((e.key === '/' || (e.ctrlKey && e.key === 'k')) && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
        return;
      }

      // Navigate results with Arrow keys
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => {
          const next = prev < results.length - 1 ? prev + 1 : prev;
          if (results[next]) {
            onAnnounce(`Result ${next + 1}: ${results[next].title}`);
          }
          return next;
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => {
          const next = prev > 0 ? prev - 1 : 0;
          if (results[next]) {
            onAnnounce(`Result ${next + 1}: ${results[next].title}`);
          }
          return next;
        });
      } else if (e.key === 'a' || e.key === 'A') {
        // Trigger autopsy if a result is selected
        if (selectedIndex >= 0 && results[selectedIndex]) {
          e.preventDefault();
          const target = results[selectedIndex];
          onOpenAutopsy(query, target.doc_id, 1);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [results, selectedIndex, query]);

  return (
    <div className="space-y-6 animate-fade-in text-slate-100">
      {/* Search Input Section */}
      <div className="p-6 rounded-2xl glass-panel bg-slate-900/60 border border-white/10 shadow-xl space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query, mode);
          }}
          className="relative flex items-center"
        >
          <Search className="absolute left-4 w-5 h-5 text-indigo-400" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search documentation, distributed systems, memory profiling... (Press '/' to focus)"
            className="w-full pl-12 pr-28 py-3.5 rounded-xl bg-slate-950/90 border border-white/15 text-slate-100 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all font-sans"
            aria-label="Search query input"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all focus-visible:ring-2"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Quick Suggestion Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Try Benchmark Queries:</span>
          {sampleQueries.map((item) => (
            <button
              key={item.label}
              onClick={() => {
                setQuery(item.q);
                handleSearch(item.q, mode);
              }}
              className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-white/10 transition-colors focus-visible:ring-2"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Retrieval Strategy Switcher */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/5 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Pipeline Strategy:</span>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-white/10">
              {[
                { id: 'hybrid_ltr', label: 'Hybrid + LTR (Production)' },
                { id: 'bm25', label: 'BM25 Baseline' },
                { id: 'dense', label: 'Dense Semantic' },
                { id: 'hybrid', label: 'Reciprocal Rank Fusion (RRF)' },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`px-3 py-1 rounded-md transition-all font-medium ${
                    mode === m.id
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  aria-pressed={mode === m.id}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {trace && (
            <div className="flex items-center gap-3 font-mono text-slate-400">
              <span className="flex items-center gap-1 text-emerald-400 font-bold">
                <Clock className="w-3.5 h-3.5" /> {trace.total_latency_ms} ms
              </span>
              <span>•</span>
              <span>{results.length} results</span>
            </div>
          )}
        </div>
      </div>

      {/* Relevance Failure Alert Banner (If present) */}
      {autopsyPreview && mode === 'bm25' && (
        <div 
          className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between gap-4 animate-fade-in"
          role="alert"
        >
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <strong className="font-semibold block text-white">Relevance Anomaly Detected by Quality Monitor</strong>
              <span>{autopsyPreview.reason}</span>
            </div>
          </div>
          <button
            onClick={() => onOpenAutopsy(query, undefined, 1)}
            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md transition-colors shrink-0 focus-visible:ring-2"
          >
            Launch Search Failure Autopsy
          </button>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-3" role="feed" aria-label="Search results list">
        {results.map((item, index) => {
          const isSelected = selectedIndex === index;
          const lang = item.language?.toLowerCase() || 'generic';
          const badgeMap: Record<string, string> = {
            python: 'badge-python',
            java: 'badge-java',
            rust: 'badge-rust',
            go: 'badge-go',
            systems: 'badge-systems',
            ir: 'badge-ir'
          };
          const badgeClass = badgeMap[lang] || 'badge-ir';

          return (
            <article
              key={item.doc_id}
              tabIndex={0}
              onFocus={() => setSelectedIndex(index)}
              className={`p-5 rounded-xl border transition-all glass-panel cursor-pointer ${
                isSelected
                  ? 'border-indigo-500 bg-indigo-950/20 shadow-lg shadow-indigo-500/10'
                  : 'border-white/10 bg-slate-900/40 hover:bg-slate-900/70'
              }`}
              aria-labelledby={`result-title-${item.doc_id}`}
            >
              <div className="flex items-start justify-between gap-4 mb-2">
                <div className="flex items-center gap-2.5">
                  <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono font-bold ${
                    index === 0 ? 'bg-indigo-600 text-white shadow' : 'bg-slate-800 text-slate-300'
                  }`}>
                    #{item.final_rank || index + 1}
                  </span>
                  <h3 id={`result-title-${item.doc_id}`} className="font-bold text-base text-white hover:text-indigo-300 transition-colors">
                    {item.title}
                  </h3>
                  <span className={`badge ${badgeClass} uppercase text-[10px] font-mono`}>
                    {lang}
                  </span>
                  {item.channel_provenance && (
                    <span className="badge bg-slate-800 text-slate-300 text-[10px]">
                      {item.channel_provenance === 'both' ? 'Lexical + Dense' : item.channel_provenance}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">
                    Score: <strong className="text-emerald-400">{item.final_score || item.score}</strong>
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenAutopsy(query, item.doc_id, 1);
                    }}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-medium border border-indigo-500/30 transition-colors focus-visible:ring-2"
                    aria-label={`Inspect ranking autopsy for ${item.title}`}
                  >
                    <Compass className="w-3.5 h-3.5" />
                    <span>Autopsy</span>
                  </button>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed line-clamp-2 mb-3">
                {item.body}
              </p>

              {/* Feature Values Inspector Strip */}
              {item.features && (
                <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-white/5 text-[11px] font-mono text-slate-400">
                  <span>BM25: <strong className="text-slate-200">{item.features.bm25_score}</strong></span>
                  <span>Dense: <strong className="text-slate-200">{item.features.dense_score}</strong></span>
                  <span>Title Match: <strong className="text-slate-200">{item.features.title_match_ratio}</strong></span>
                  <span>Language Affinity: <strong className={item.features.language_affinity < 0 ? 'text-rose-400' : 'text-emerald-400'}>
                    {item.features.language_affinity}
                  </strong></span>
                  <span>Freshness: <strong className="text-slate-200">{item.features.freshness_score}</strong></span>
                  {item.rank_delta !== undefined && item.rank_delta !== 0 && (
                    <span className="ml-auto font-bold text-emerald-400 flex items-center gap-0.5">
                      <ArrowUpDown className="w-3 h-3" /> Promoted by LTR ({item.rank_delta > 0 ? `+${item.rank_delta}` : item.rank_delta})
                    </span>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
};
