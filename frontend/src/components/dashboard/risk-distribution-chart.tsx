'use client';

import React from 'react';
import { RiskDistributionBand } from '@/types/analytics';

interface RiskDistributionChartProps {
  distribution?: RiskDistributionBand[];
}

export function RiskDistributionChart({ distribution = [] }: RiskDistributionChartProps) {
  // If distribution from API trends:
  const bands = distribution.length > 0 ? distribution : [
    { band: 'Neutral / Routine (0-14)', count: 395120 },
    { band: 'Low Risk (15-44)', count: 64119 },
    { band: 'Medium Risk (45-69)', count: 18420 },
    { band: 'High Risk (70-84)', count: 3940 },
    { band: 'Critical Risk (85-100)', count: 1211 },
  ];

  const total = bands.reduce((acc, curr) => acc + curr.count, 0) || 1;

  const bandColors: Record<string, { bar: string; text: string }> = {
    'Neutral / Routine (0-14)': { bar: 'bg-slate-500', text: 'text-slate-400' },
    'Routine (0-24)': { bar: 'bg-slate-500', text: 'text-slate-400' },
    'Low Risk (15-44)': { bar: 'bg-emerald-500', text: 'text-emerald-400' },
    'Low (25-49)': { bar: 'bg-emerald-500', text: 'text-emerald-400' },
    'Medium Risk (45-69)': { bar: 'bg-amber-500', text: 'text-amber-400' },
    'Elevated (50-74)': { bar: 'bg-amber-500', text: 'text-amber-400' },
    'High Risk (70-84)': { bar: 'bg-orange-500', text: 'text-orange-400' },
    'High Priority (75-100)': { bar: 'bg-orange-500', text: 'text-orange-400' },
    'Critical Risk (85-100)': { bar: 'bg-rose-500', text: 'text-rose-400' },
  };

  return (
    <div className="p-4 sm:p-5 rounded-lg border border-slate-800/80 bg-[#111722] space-y-4">
      <div>
        <h3 className="text-xs font-semibold text-slate-100 font-mono uppercase tracking-wider">
          Portfolio Risk Tier Stratification
        </h3>
        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
          Distribution across <span className="text-slate-200 tabular-nums">{total.toLocaleString()}</span> monitored transactions
        </p>
      </div>

      <div className="space-y-3 pt-1">
        {bands.map((b) => {
          const pct = ((b.count / total) * 100).toFixed(1);
          const color = bandColors[b.band] || { bar: 'bg-slate-500', text: 'text-slate-400' };

          return (
            <div key={b.band} className="space-y-1">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className={`${color.text} text-[11px] font-medium`}>{b.band}</span>
                <span className="text-slate-400 text-[11px] tabular-nums">
                  {b.count.toLocaleString()} <span className="text-slate-500 font-normal">({pct}%)</span>
                </span>
              </div>
              <div className="h-1.5 w-full bg-[#0B0F17] rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${Math.max(Number(pct), 0.5)}%` }}
                  className={`h-full rounded-full ${color.bar}`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
