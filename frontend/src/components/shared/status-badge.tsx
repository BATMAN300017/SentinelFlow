'use client';

import React from 'react';
import { RISK_BANDS, getRiskBand } from '@/lib/utils';
import { SEVERITIES, CASE_STATUSES } from '@/lib/constants';

interface StatusBadgeProps {
  type: 'risk' | 'severity' | 'case_status' | 'channel';
  value: string | number;
  className?: string;
}

export function StatusBadge({ type, value, className = '' }: StatusBadgeProps) {
  if (type === 'risk') {
    const score = Number(value) || 0;
    const bandKey = getRiskBand(score);
    const band = RISK_BANDS[bandKey];
    return (
      <span
        className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold font-mono border ${band.color} ${className}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${band.dot}`} />
        <span>{score.toFixed(0)}</span>
      </span>
    );
  }

  if (type === 'severity') {
    const key = String(value).toUpperCase() as keyof typeof SEVERITIES;
    const sev = SEVERITIES[key] || SEVERITIES.LOW;
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono uppercase tracking-wider border ${sev.bg} ${sev.text} ${sev.border} ${className}`}
      >
        {sev.label}
      </span>
    );
  }

  if (type === 'case_status') {
    const key = String(value).toUpperCase() as keyof typeof CASE_STATUSES;
    const st = CASE_STATUSES[key] || CASE_STATUSES.NEW;
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium font-mono border ${st.color} ${className}`}
      >
        {st.label}
      </span>
    );
  }

  if (type === 'channel') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 ${className}`}
      >
        {String(value)}
      </span>
    );
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 ${className}`}>
      {String(value)}
    </span>
  );
}
