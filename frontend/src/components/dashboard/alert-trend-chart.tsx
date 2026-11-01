'use client';

import React from 'react';

interface AlertTrendChartProps {
  totalAlerts?: number;
}

export function AlertTrendChart({ totalAlerts = 157 }: AlertTrendChartProps) {
  const days = [
    { label: 'Mon', count: 18, critical: 2 },
    { label: 'Tue', count: 24, critical: 4 },
    { label: 'Wed', count: 29, critical: 3 },
    { label: 'Thu', count: 22, critical: 1 },
    { label: 'Fri', count: 35, critical: 6 },
    { label: 'Sat', count: 14, critical: 1 },
    { label: 'Sun', count: 15, critical: 2 },
  ];

  const max = Math.max(...days.map((d) => d.count));

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            7-Day Alert Generation Trend
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            {totalAlerts} total detected incidents requiring triage
          </p>
        </div>
        <div className="flex items-center space-x-3 text-[11px] font-mono">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-slate-400">Elevated</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-slate-400">Critical</span>
          </span>
        </div>
      </div>

      <div className="h-44 flex items-end justify-between gap-4 pt-6 pb-2 px-2">
        {days.map((day) => {
          const heightPct = Math.round((day.count / max) * 100);
          return (
            <div key={day.label} className="flex-1 flex flex-col items-center gap-2">
              <div className="w-full flex flex-col items-center justify-end h-32">
                <div
                  style={{ height: `${heightPct}%` }}
                  className="w-full max-w-[32px] rounded-t bg-gradient-to-t from-amber-600/50 to-amber-400 relative group transition-all"
                >
                  <span className="text-[10px] font-mono text-amber-300 opacity-0 group-hover:opacity-100 transition absolute -top-5 left-1/2 -translate-x-1/2">
                    {day.count}
                  </span>
                </div>
              </div>
              <span className="text-[11px] font-mono text-slate-400">{day.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
