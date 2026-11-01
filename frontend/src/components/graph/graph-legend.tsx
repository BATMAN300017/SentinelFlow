'use client';

import React from 'react';

export function GraphLegend() {
  const items = [
    { label: 'Originator / Routine (0-24)', color: 'bg-emerald-500' },
    { label: 'Low Risk (25-49)', color: 'bg-sky-500' },
    { label: 'Mule Intermediary (50-74)', color: 'bg-amber-500' },
    { label: 'Sink / Flagged Syndicate (75+)', color: 'bg-rose-500' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-4 p-3 rounded-xl border border-slate-800 bg-slate-900/60 text-xs font-mono">
      <span className="text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
        Node Classification:
      </span>
      {items.map((it) => (
        <div key={it.label} className="flex items-center space-x-1.5">
          <span className={`w-2 h-2 rounded-full ${it.color}`} />
          <span className="text-slate-300">{it.label}</span>
        </div>
      ))}
    </div>
  );
}
