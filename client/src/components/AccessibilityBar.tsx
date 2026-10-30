import React, { useState } from 'react';
import { Eye, Keyboard, Volume2, HelpCircle } from 'lucide-react';

interface AccessibilityBarProps {
  screenReaderAnnouncement: string;
}

export const AccessibilityBar: React.FC<AccessibilityBarProps> = ({ screenReaderAnnouncement }) => {
  const [highContrast, setHighContrast] = useState(false);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  const toggleContrast = () => {
    const next = !highContrast;
    setHighContrast(next);
    if (next) {
      document.body.classList.add('high-contrast');
    } else {
      document.body.classList.remove('high-contrast');
    }
  };

  return (
    <header className="border-b border-white/10 bg-black/40 backdrop-blur-md px-4 py-2 flex flex-wrap items-center justify-between gap-4 text-xs">
      {/* ARIA Live Region for screen readers */}
      <div 
        role="status" 
        aria-live="polite" 
        aria-atomic="true" 
        className="sr-only"
        id="sr-live-announcements"
      >
        {screenReaderAnnouncement}
      </div>

      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 font-medium text-slate-300">
          <Volume2 className="w-3.5 h-3.5 text-indigo-400" aria-hidden="true" />
          <span className="text-slate-400">Live Status:</span>
          <span className="text-slate-200 font-mono italic max-w-md truncate">
            {screenReaderAnnouncement || "Search engine ready. Press '/' to search."}
          </span>
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleContrast}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-white/10 transition-colors focus-visible:ring-2"
          aria-pressed={highContrast}
          aria-label="Toggle high contrast accessibility mode"
        >
          <Eye className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
          <span>{highContrast ? "Standard Theme" : "High Contrast"}</span>
        </button>

        <button
          onClick={() => setShowKeyboardHelp(!showKeyboardHelp)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-white/10 transition-colors focus-visible:ring-2"
          aria-expanded={showKeyboardHelp}
          aria-label="Keyboard navigation shortcut legend"
        >
          <Keyboard className="w-3.5 h-3.5 text-indigo-400" aria-hidden="true" />
          <span>Keyboard Shortcuts</span>
        </button>
      </div>

      {showKeyboardHelp && (
        <div 
          className="w-full mt-2 p-3 rounded-lg bg-slate-900 border border-indigo-500/30 text-slate-300 animate-fade-in"
          role="region"
          aria-label="Keyboard shortcuts instructions"
        >
          <div className="flex justify-between items-center mb-2 font-semibold text-indigo-300">
            <span className="flex items-center gap-1">
              <HelpCircle className="w-4 h-4" /> Keyboard Navigation (Accessible First)
            </span>
            <button 
              onClick={() => setShowKeyboardHelp(false)}
              className="text-slate-400 hover:text-white"
              aria-label="Close keyboard shortcuts dialog"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono">
            <div><kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">/</kbd> or <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">Ctrl+K</kbd> : Focus Search</div>
            <div><kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">↓</kbd> / <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">↑</kbd> : Navigate Results</div>
            <div><kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">A</kbd> : Open Autopsy on Result</div>
            <div><kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-white/20 text-white">Esc</kbd> : Close Modals</div>
          </div>
        </div>
      )}
    </header>
  );
};
