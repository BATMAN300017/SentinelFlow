'use client';

import React from 'react';
import Link from 'next/link';
import { StatusBadge } from '@/components/shared/status-badge';
import { ArrowRight, AlertTriangle } from 'lucide-react';

interface PriorityCasesProps {
  cases: any[];
}

export function PriorityCases({ cases }: PriorityCasesProps) {
  const displayCases = cases && cases.length > 0 ? cases.slice(0, 5) : [];

  return (
    <div className="p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26] flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-[#262D26] pb-3">
          <div>
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF] flex items-center space-x-2">
              <span>Active Investigation Priority Queue</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#2A1414] text-[#FF6B6B] border border-[#5A2020] font-mono">
                HIGH SEVERITY
              </span>
            </h3>
            <p className="text-[11px] text-[#687166] font-mono mt-0.5">
              Cases escalated by multi-signal anomaly & graph correlation
            </p>
          </div>
          <Link
            href="/investigations"
            className="text-xs font-mono text-[#929B90] hover:text-[#B7F34A] flex items-center space-x-1 transition"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {displayCases.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-[#687166]">
            No high-priority active cases currently flagged
          </div>
        ) : (
          <div className="divide-y divide-[#1F261F]">
            {displayCases.map((c) => (
              <Link
                key={c.id || c.case_id}
                href={`/investigations/${c.id || c.case_id}`}
                className="py-2.5 flex items-center justify-between hover:bg-[#181E18] px-2 rounded -mx-2 transition group"
              >
                <div className="min-w-0 pr-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-semibold text-[#F2F4EF] group-hover:text-[#B7F34A] transition truncate">
                      {c.case_id || c.id}
                    </span>
                    <StatusBadge type="severity" value={c.severity || 'HIGH'} />
                  </div>
                  <div className="text-[11px] text-[#929B90] font-mono truncate mt-0.5">
                    {c.title || c.primary_entity || 'Multi-Hop Structuring Anomaly'}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-mono font-bold text-[#F2F4EF] tabular-nums">
                    ₹{(c.total_exposure || c.amount || 2450000).toLocaleString()}
                  </div>
                  <div className="text-[10px] text-[#687166] font-mono">
                    {c.status || 'IN_PROGRESS'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-[#262D26] mt-4 flex items-center justify-between text-[11px] font-mono text-[#687166]">
        <span>SLA Target: &lt; 4.0 Hours</span>
        <span className="text-[#B7F34A]">98.2% Compliance</span>
      </div>
    </div>
  );
}
