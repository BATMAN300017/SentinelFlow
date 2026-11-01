'use client';

import React from 'react';

interface TransactionVolumeChartProps {
  throughputTpm?: number;
}

export function TransactionVolumeChart({ throughputTpm = 42.5 }: TransactionVolumeChartProps) {
  // Simulated normalized recent hourly volume buckets
  const bars = [28, 35, 42, 38, 55, 49, 62, 70, 65, 80, 75, 88, 92, 85, 96, 100, 91, 84, 78, 82, 89, 94, 91, 87];

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            Transaction Throughput (24-Hour Velocity)
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Calibrated real-time stream • {throughputTpm} TPM current load
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-sky-950/80 text-sky-400 border border-sky-800/80">
          Live Window
        </span>
      </div>

      <div className="h-44 flex items-end justify-between gap-1.5 pt-6 pb-2 px-1">
        {bars.map((height, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              style={{ height: `${height}%` }}
              className="w-full rounded-t bg-gradient-to-t from-sky-600/40 via-sky-500/70 to-sky-400 group-hover:from-sky-500 group-hover:to-sky-300 transition-all duration-200"
            />
            <span className="text-[9px] font-mono text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity absolute -top-5">
              {Math.round(height * (throughputTpm / 70))}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-850 pt-2">
        <span>-24h</span>
        <span>-18h</span>
        <span>-12h</span>
        <span>-6h</span>
        <span>Current (0m)</span>
      </div>
    </div>
  );
}
