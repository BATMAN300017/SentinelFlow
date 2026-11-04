'use client';

import React from 'react';
import { GitFork, AlertTriangle } from 'lucide-react';

export function SuspiciousPathPanel() {
  const chains = [
    {
      id: 'CHAIN-01',
      pattern: 'Rapid Fan-In Mule Consolidation (3-Hop)',
      hops: ['ACCT_000038', 'ACCT_000104', 'ACCT_000892'],
      velocitySeconds: 142,
      totalVolume: '₹485,000',
      risk: 'CRITICAL',
    },
    {
      id: 'CHAIN-02',
      pattern: 'Circular Layering Sweep',
      hops: ['ACCT_000104', 'ACCT_000219', 'ACCT_000892'],
      velocitySeconds: 310,
      totalVolume: '₹240,000',
      risk: 'HIGH',
    },
  ];

  return (
    <div className="p-6 rounded-2xl border border-slate-800/80 bg-[#111722] shadow-lg space-y-4">
      <div className="flex items-center space-x-2">
        <GitFork className="w-4 h-4 text-rose-400" />
        <h3 className="text-sm font-semibold text-slate-100 font-mono">
          Identified Mule Pathways & Circular Flows
        </h3>
      </div>

      <div className="space-y-3">
        {chains.map((c) => (
          <div key={c.id} className="p-4 rounded-xl border border-slate-800/80 bg-[#0B0F17] space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-slate-200">{c.pattern}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                c.risk === 'CRITICAL'
                  ? 'bg-rose-950/80 text-rose-400 border border-rose-800'
                  : 'bg-orange-950/80 text-orange-400 border border-orange-800'
              }`}>
                {c.risk}
              </span>
            </div>

            <div className="flex items-center space-x-2 text-xs font-mono text-slate-300 py-1">
              {c.hops.map((hop, i) => (
                <React.Fragment key={hop}>
                  <span className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">
                    {hop}
                  </span>
                  {i < c.hops.length - 1 && <span className="text-emerald-400 font-bold">&rarr;</span>}
                </React.Fragment>
              ))}
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
              <span className="tabular-nums">Velocity: {c.velocitySeconds}s traversal</span>
              <span className="text-slate-300 font-bold tabular-nums">Total Flow: {c.totalVolume}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
