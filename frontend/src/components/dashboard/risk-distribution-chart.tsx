'use client';

import React from 'react';
import { RiskDistributionBand } from '@/types/analytics';

interface RiskDistributionChartProps {
  distribution?: RiskDistributionBand[];
}

export function RiskDistributionChart({ distribution = [] }: RiskDistributionChartProps) {
  // If distribution from API trends:
  const bands = distribution.length > 0 ? distribution : [
    { band: 'Routine (0-24)', count: 423586 },
    { band: 'Low (25-49)', count: 35653 },
    { band: 'Elevated (50-74)', count: 18420 },
    { band: 'High Priority (75-100)', count: 5151 },
  ];

  const total = bands.reduce((acc, curr) => acc + curr.count, 0) || 1;

  const bandColors: Record<string, { bar: string; text: string }> = {
    'Routine (0-24)': { bar: 'bg-emerald-500', text: 'text-emerald-400' },
    'Low (25-49)': { bar: 'bg-sky-500', text: 'text-sky-400' },
    'Elevated (50-74)': { bar: 'bg-amber-500', text: 'text-amber-400' },
    'High Priority (75-100)': { bar: 'bg-rose-500', text: 'text-rose-400' },
  };

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-100 font-mono">
          Portfolio Risk Tier Breakdown
        </h3>
        <p className="text-xs text-slate-400 font-mono mt-0.5">
          Stratification across {total.toLocaleString()} ingested transactions
        </p>
      </div>

      <div className="space-y-3 pt-2">
        {bands.map((b) => {
          const pct = ((b.count / total) * 100).toFixed(1);
          const color = bandColors[b.band] || { bar: 'bg-slate-500', text: 'text-slate-400' };

          return (
            <div key={b.band} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className={color.text}>{b.band}</span>
                <span className="text-slate-400">
                  {b.count.toLocaleString()} <span className="text-slate-600">({pct}%)</span>
                </span>
              </div>
              <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${Math.max(Number(pct), 1)}%` }}
                  className={`h-full rounded-full ${color.bar} transition-all duration-500`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
