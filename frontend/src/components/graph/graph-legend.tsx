'use client';

import React from 'react';

export function GraphLegend() {
  const items = [
    { label: 'Routine / Neutral (0-19)', color: 'bg-slate-400' },
    { label: 'Low Risk (20-39)', color: 'bg-emerald-400' },
    { label: 'Medium Risk (40-59)', color: 'bg-amber-400' },
    { label: 'High Risk (60-79)', color: 'bg-orange-400' },
    { label: 'Critical Risk (80-100)', color: 'bg-rose-400' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-4 p-3 rounded-xl border border-slate-800/80 bg-[#111722] text-xs font-mono">
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
