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
  accent?: 'lime' | 'amber' | 'rose' | 'neutral' | 'sky' | 'emerald';
}

export function MetricCard({
  label,
  value,
  subtitle,
  delta,
  icon,
  accent = 'neutral',
}: MetricCardProps) {
  // Institutional border indicator (clean hairline accent)
  const accentBorder = {
    lime: 'border-l-2 border-l-[#B7F34A]',
    emerald: 'border-l-2 border-l-[#B7F34A]',
    amber: 'border-l-2 border-l-[#FFB800]',
    rose: 'border-l-2 border-l-[#FF4D4D]',
    sky: 'border-l-2 border-l-[#929B90]',
    neutral: 'border-l-2 border-l-[#364036]',
  }[accent];

  return (
    <div
      className={`p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26] hover:border-[#364036] transition-colors ${accentBorder}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#929B90]">
          {label}
        </span>
        {icon && <div className="text-[#687166] shrink-0">{icon}</div>}
      </div>

      <div className="mt-2.5 flex items-baseline space-x-2">
        <span className="text-2xl sm:text-3xl font-bold font-mono text-[#F2F4EF] tracking-tight tabular-nums">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
        {delta && (
          <span
            className={`inline-flex items-center text-xs font-mono font-medium ${
              delta.isNeutral
                ? 'text-[#929B90]'
                : delta.isPositive
                ? 'text-[#B7F34A]'
                : 'text-[#FF6B6B]'
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

      {subtitle && <p className="mt-1.5 text-[11px] text-[#687166] font-mono truncate">{subtitle}</p>}
    </div>
  );
}
