'use client';

import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  delta?: {
    value: string;
    isPositive?: boolean;
    isNeutral?: boolean;
  };
  icon?: React.ReactNode;
  accent?: 'sky' | 'emerald' | 'amber' | 'rose';
}

export function MetricCard({
  label,
  value,
  subtitle,
  delta,
  icon,
  accent = 'sky',
}: MetricCardProps) {
  const accentBorder = {
    sky: 'border-l-2 border-l-slate-700',
    emerald: 'border-l-2 border-l-emerald-500/80',
    amber: 'border-l-2 border-l-amber-500/80',
    rose: 'border-l-2 border-l-rose-500/80',
  }[accent];

  return (
    <div
      className={`p-4 sm:p-5 rounded-lg border border-slate-800/80 bg-[#111722] hover:border-slate-700/90 transition-colors ${accentBorder}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {icon && <div className="text-slate-500 shrink-0">{icon}</div>}
      </div>

      <div className="mt-2.5 flex items-baseline space-x-2">
        <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight tabular-nums">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
        {delta && (
          <span
            className={`inline-flex items-center text-xs font-mono font-medium ${
              delta.isNeutral
                ? 'text-slate-400'
                : delta.isPositive
                ? 'text-emerald-400'
                : 'text-rose-400'
            }`}
          >
            {delta.isNeutral ? (
              <Minus className="w-3 h-3 mr-0.5" />
            ) : delta.isPositive ? (
              <ArrowUpRight className="w-3 h-3 mr-0.5" />
            ) : (
              <ArrowDownRight className="w-3 h-3 mr-0.5" />
            )}
            {delta.value}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-1 text-[11px] text-slate-400 font-mono">{subtitle}</p>}
    </div>
  );
}
