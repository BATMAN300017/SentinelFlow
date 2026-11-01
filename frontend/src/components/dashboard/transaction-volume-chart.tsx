'use client';

import React from 'react';

interface TransactionVolumeChartProps {
  throughputTpm?: number;
}

export function TransactionVolumeChart({ throughputTpm = 42.5 }: TransactionVolumeChartProps) {
  // Simulated normalized recent hourly volume buckets
  const bars = [28, 35, 42, 38, 55, 49, 62, 70, 65, 80, 75, 88, 92, 85, 96, 100, 91, 84, 78, 82, 89, 94, 91, 87];

  return (
    <div className="p-4 sm:p-5 rounded-lg border border-slate-800/80 bg-[#111722] space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-slate-100 font-mono uppercase tracking-wider">
            Transaction Ingestion Velocity (24h Histogram)
          </h3>
          <p className="text-[11px] text-slate-400 font-mono mt-0.5">
            Calibrated stream rate &bull; <span className="text-slate-200 tabular-nums">{throughputTpm} TPM</span> current load
          </p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
          Rolling 24h
        </span>
      </div>

      <div className="h-40 flex items-end justify-between gap-1 pt-6 pb-2 px-1">
        {bars.map((height, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              style={{ height: `${height}%` }}
              className="w-full rounded-t bg-slate-700/60 hover:bg-emerald-500/70 transition-colors"
            />
            <span className="text-[9px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity absolute -top-5 tabular-nums pointer-events-none">
              {Math.round(height * (throughputTpm / 70))}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-800/80 pt-2">
        <span>-24h</span>
        <span>-18h</span>
        <span>-12h</span>
        <span>-6h</span>
        <span>Current (0m)</span>
      </div>
    </div>
  );
}
