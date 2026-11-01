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
  const accentStyles = {
    sky: 'border-sky-500/30 shadow-sky-500/5',
    emerald: 'border-emerald-500/30 shadow-emerald-500/5',
    amber: 'border-amber-500/30 shadow-amber-500/5',
    rose: 'border-rose-500/30 shadow-rose-500/5',
  }[accent];

  return (
    <div
      className={`p-5 rounded-2xl border bg-slate-900/80 shadow-lg backdrop-blur-sm transition-all hover:border-slate-700/80 ${accentStyles}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>

      <div className="mt-3 flex items-baseline space-x-2">
        <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight">
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

      {subtitle && <p className="mt-1.5 text-xs text-slate-400 font-mono">{subtitle}</p>}
    </div>
  );
}
