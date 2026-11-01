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
    <div className="p-4 sm:p-5 rounded-lg border border-slate-800/80 bg-[#111722] space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-orange-400" />
          <h3 className="text-xs font-semibold text-slate-100 font-mono uppercase tracking-wider">
            Active Priority Dossiers
          </h3>
        </div>
        <Link
          href="/investigations"
          className="text-xs font-mono text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
        >
          <span>All Cases</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-2">
        {cases.length > 0 ? (
          cases.slice(0, 4).map((c) => (
            <Link
              key={c.id}
              href={`/investigations?id=${c.id}`}
              className="p-3 rounded-md border border-slate-800/80 bg-[#0B0F17] hover:bg-slate-900/90 hover:border-slate-700 transition-colors flex items-center justify-between group block"
            >
              <div className="space-y-1 pr-3 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-slate-200 group-hover:text-emerald-400 transition-colors">
                    {c.case_number}
                  </span>
                  <StatusBadge type="severity" value={c.priority} />
                </div>
                <h4 className="text-xs text-slate-300 font-medium truncate">{c.title}</h4>
              </div>
              <div className="shrink-0">
                <StatusBadge type="case_status" value={c.status} />
              </div>
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
