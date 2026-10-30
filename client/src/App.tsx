import React, { useState, useEffect } from 'react';
import { Search, FlaskConical, Database, Activity } from 'lucide-react';
import { AccessibilityBar } from './components/AccessibilityBar';
import { SearchInterface } from './components/SearchInterface';
import { LaboratoryView } from './components/LaboratoryView';
import { DistributedCluster } from './components/DistributedCluster';
import { ObservatoryView } from './components/ObservatoryView';
import { AutopsyModal } from './components/AutopsyModal';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'search' | 'lab' | 'cluster' | 'observatory'>('search');
  const [announcement, setAnnouncement] = useState<string>('Atlas Search initialized. Welcome to the search quality platform.');
  const [autopsyReport, setAutopsyReport] = useState<any>(null);

  const announce = (msg: string) => {
    setAnnouncement(msg);
  };

  const handleOpenAutopsy = async (query: string, targetDocId?: number, winnerRank: number = 1) => {
    announce(`Generating Search Failure Autopsy for ${query}...`);
    try {
      const res = await fetch('/api/autopsy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, target_doc_id: targetDocId, winner_rank: winnerRank })
      });
      const data = await res.json();
      setAutopsyReport(data);
      announce(`Search Failure Autopsy ready for query ${query}.`);
    } catch (err) {
      console.error(err);
      announce('Failed to generate autopsy report.');
    }
  };

  // Keyboard shortcut listener for tab switching
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
        return;
      }
      if (e.key === '1') {
        setActiveTab('search');
        announce('Switched to Search & Autopsy View.');
      } else if (e.key === '2') {
        setActiveTab('lab');
        announce('Switched to Learning-to-Rank Laboratory.');
      } else if (e.key === '3') {
        setActiveTab('cluster');
        announce('Switched to Distributed Cluster Subsystem.');
      } else if (e.key === '4') {
        setActiveTab('observatory');
        announce('Switched to Search Quality Observatory.');
      } else if (e.key === 'Escape' && autopsyReport) {
        setAutopsyReport(null);
        announce('Closed autopsy modal.');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [autopsyReport]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans">
      {/* Top Accessibility Bar */}
      <AccessibilityBar screenReaderAnnouncement={announcement} />

      {/* Main Navigation Bar */}
      <nav 
        className="border-b border-white/10 bg-slate-900/60 backdrop-blur-md px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-30"
        aria-label="Main application navigation"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30 text-white font-bold text-lg">
            ⚡
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight text-white flex items-center gap-2">
              Atlas Search
              <span className="badge bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono">
                v1.0 RESEARCH
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium">Search Retrieval &amp; Quality Engineering Platform</p>
          </div>
        </div>

        {/* Tab Buttons */}
        <div className="flex rounded-xl bg-slate-950 p-1 border border-white/10" role="tablist">
          {[
            { id: 'search', label: 'Search & Autopsy', icon: Search, shortcut: '1' },
            { id: 'lab', label: 'LTR Laboratory', icon: FlaskConical, shortcut: '2' },
            { id: 'cluster', label: 'Distributed Index', icon: Database, shortcut: '3' },
            { id: 'observatory', label: 'Quality Observatory', icon: Activity, shortcut: '4' },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => {
                  setActiveTab(tab.id as any);
                  announce(`Switched to ${tab.label}`);
                }}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all focus-visible:ring-2 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{tab.label}</span>
                <kbd className="hidden md:inline px-1 py-0.2 bg-black/40 text-[9px] text-slate-400 rounded font-mono border border-white/10">
                  {tab.shortcut}
                </kbd>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8" id="main-content">
        {activeTab === 'search' && (
          <SearchInterface onOpenAutopsy={handleOpenAutopsy} onAnnounce={announce} />
        )}
        {activeTab === 'lab' && (
          <LaboratoryView onAnnounce={announce} />
        )}
        {activeTab === 'cluster' && (
          <DistributedCluster onAnnounce={announce} />
        )}
        {activeTab === 'observatory' && (
          <ObservatoryView onAnnounce={announce} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-black/60 px-6 py-4 text-center text-xs text-slate-500 font-mono">
        Atlas Search · Inverted Index · BM25Okapi · Vector Semantic Search · Learning-to-Rank · Search Failure Autopsy
      </footer>

      {/* Autopsy Diagnostic Modal */}
      {autopsyReport && (
        <AutopsyModal
          report={autopsyReport}
          onClose={() => setAutopsyReport(null)}
          onAnnounce={announce}
        />
      )}
    </div>
  );
};

export default App;
