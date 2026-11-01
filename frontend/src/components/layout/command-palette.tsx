'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, ArrowRight, X } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

const COMMANDS = [
  { name: 'Command Center', path: '/dashboard', section: 'Navigation' },
  { name: 'Live Transactions & Flow Analyzer', path: '/transactions', section: 'Navigation' },
  { name: 'Alerts Queue & Triage', path: '/alerts', section: 'Navigation' },
  { name: 'Investigation Workspace', path: '/investigations', section: 'Navigation' },
  { name: 'Fund Flow Tracing (Sankey)', path: '/fund-flow', section: 'Surveillance' },
  { name: 'Network Intelligence Graph', path: '/network', section: 'Surveillance' },
  { name: 'Entity Profiles & Accounts', path: '/entities', section: 'Surveillance' },
  { name: 'Model Intelligence & Explainability', path: '/intelligence', section: 'Machine Learning' },
  { name: 'Model Learning & Feedback Loop', path: '/feedback', section: 'Machine Learning' },
  { name: 'Detection Rules & Heuristics', path: '/rules', section: 'Governance' },
  { name: 'Audit Trail & Compliance', path: '/audit', section: 'Governance' },
  { name: 'System Settings & Architecture', path: '/settings', section: 'Configuration' },
];

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(); // parent handles toggle
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = COMMANDS.filter((cmd) =>
    cmd.name.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (path: string) => {
    router.push(path);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-12 sm:pt-24 px-3 sm:px-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-fade-in">
        <div className="flex items-center px-4 py-3 border-b border-slate-800">
          <Search className="w-5 h-5 text-slate-500 mr-3" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a page or command..."
            className="flex-1 bg-transparent text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-72 overflow-y-auto p-2 divide-y divide-slate-850">
          {filtered.length > 0 ? (
            filtered.map((cmd) => (
              <button
                key={cmd.path}
                onClick={() => handleSelect(cmd.path)}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-mono text-left text-slate-300 hover:bg-slate-800 hover:text-sky-400 transition group"
              >
                <span>{cmd.name}</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition text-sky-400" />
              </button>
            ))
          ) : (
            <div className="p-4 text-center text-xs font-mono text-slate-500">
              No matching commands found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
