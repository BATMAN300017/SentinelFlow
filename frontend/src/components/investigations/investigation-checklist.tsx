'use client';

import React, { useState } from 'react';
import { CheckSquare, Square } from 'lucide-react';

interface ChecklistItem {
  id: string;
  label: string;
  checked: boolean;
}

export function InvestigationChecklist() {
  const [items, setItems] = useState<ChecklistItem[]>([
    { id: '1', label: 'Verify beneficiary KYC documentation status', checked: true },
    { id: '2', label: 'Check domestic and international mule databases', checked: true },
    { id: '3', label: 'Verify multi-hop transaction path distance <= 3', checked: true },
    { id: '4', label: 'Cross-check against known high-risk IP and ASN ranges', checked: false },
    { id: '5', label: 'Ensure supervisor approval obtained for SAR filing', checked: false },
  ]);

  const toggle = (id: string) => {
    setItems(items.map((it) => (it.id === id ? { ...it, checked: !it.checked } : it)));
  };

  const completed = items.filter((it) => it.checked).length;

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-100 font-mono">
          Regulatory Compliance Checklist
        </h3>
        <span className="text-xs font-mono text-sky-400">
          {completed}/{items.length} completed
        </span>
      </div>

      <div className="space-y-2">
        {items.map((it) => (
          <button
            key={it.id}
            onClick={() => toggle(it.id)}
            className="w-full flex items-center space-x-3 p-2.5 rounded-xl border border-slate-850 bg-slate-950/40 text-left hover:bg-slate-800/40 transition group"
          >
            {it.checked ? (
              <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-slate-600 group-hover:text-slate-400 shrink-0" />
            )}
            <span
              className={`text-xs font-mono leading-relaxed ${
                it.checked ? 'text-slate-400 line-through' : 'text-slate-200'
              }`}
            >
              {it.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
