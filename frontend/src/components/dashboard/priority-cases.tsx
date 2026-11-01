'use client';

import React from 'react';
import Link from 'next/link';
import { InvestigationCase } from '@/types/investigation';
import { StatusBadge } from '@/components/shared/status-badge';
import { ArrowRight, ShieldAlert } from 'lucide-react';

interface PriorityCasesProps {
  cases?: InvestigationCase[];
}

export function PriorityCases({ cases = [] }: PriorityCasesProps) {
  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            Active Priority Investigations
          </h3>
        </div>
        <Link
          href="/investigations"
          className="text-xs font-mono text-sky-400 hover:text-sky-300 flex items-center space-x-1"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-2.5">
        {cases.length > 0 ? (
          cases.slice(0, 4).map((c) => (
            <Link
              key={c.id}
              href={`/investigations/${c.id}`}
              className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:bg-slate-800/50 hover:border-slate-700 transition flex items-center justify-between group block"
            >
              <div className="space-y-1 pr-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-sky-400 group-hover:text-sky-300 transition">
                    {c.case_number}
                  </span>
                  <StatusBadge type="severity" value={c.priority} />
                </div>
                <h4 className="text-xs text-slate-300 font-medium line-clamp-1">{c.title}</h4>
              </div>
              <StatusBadge type="case_status" value={c.status} />
            </Link>
          ))
        ) : (
          <div className="py-8 text-center text-xs font-mono text-slate-500">
            No active high priority cases.
          </div>
        )}
      </div>
    </div>
  );
}
