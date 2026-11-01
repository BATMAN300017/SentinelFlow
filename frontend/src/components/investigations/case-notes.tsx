'use client';

import React, { useState } from 'react';
import { CaseNote } from '@/types/investigation';
import { MessageSquare, Send } from 'lucide-react';

interface CaseNotesProps {
  notes?: CaseNote[];
  onAddNote?: (text: string) => void;
}

export function CaseNotes({ notes = [], onAddNote }: CaseNotesProps) {
  const [newNote, setNewNote] = useState('');
  const [localNotes, setLocalNotes] = useState<CaseNote[]>(
    notes.length > 0
      ? notes
      : [
          {
            id: 'NOTE-1',
            author: 'Sarah Chen (Senior Investigator)',
            text: 'Mule account shows synchronous sweep patterns immediately upon RTGS credit arrival. Proceeding with SAR drafting.',
            created_at: '2026-11-01T06:14:00Z',
          },
        ]
  );

  const handlePost = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    const note: CaseNote = {
      id: `NOTE-${Date.now()}`,
      author: 'Current Investigator',
      text: newNote.trim(),
      created_at: new Date().toISOString(),
    };
    setLocalNotes([note, ...localNotes]);
    if (onAddNote) onAddNote(newNote.trim());
    setNewNote('');
  };

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center space-x-2">
        <MessageSquare className="w-4 h-4 text-sky-400" />
        <h3 className="text-sm font-semibold text-slate-100 font-mono">Investigator Log Notes</h3>
      </div>

      <form onSubmit={handlePost} className="flex gap-2">
        <input
          type="text"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder="Append timestamped analyst note..."
          className="flex-1 px-4 py-2 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
        />
        <button
          type="submit"
          className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-sky-600 hover:bg-sky-500 text-white transition flex items-center space-x-1.5"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Post</span>
        </button>
      </form>

      <div className="space-y-3 pt-2">
        {localNotes.map((n) => (
          <div key={n.id} className="p-3.5 rounded-xl border border-slate-850 bg-slate-950/60 space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="font-bold text-sky-400">{n.author}</span>
              <span className="text-slate-500">{new Date(n.created_at).toLocaleTimeString()}</span>
            </div>
            <p className="text-xs font-mono text-slate-300 leading-relaxed">{n.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
