'use client';

import React from 'react';
import { Alert } from '@/types/index';
import { StatusBadge } from '@/components/shared/status-badge';
import Link from 'next/link';
import { ShieldAlert, ArrowRight, UserCheck } from 'lucide-react';

interface AlertCardProps {
  alert: Alert;
  onInvestigate?: (id: string) => void;
  isInvestigating?: boolean;
}

export function AlertCard({ alert, onInvestigate, isInvestigating }: AlertCardProps) {
  return (
    <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4 hover:border-slate-700 transition">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold text-sky-400">{alert.alert_ref}</span>
            <StatusBadge type="severity" value={alert.severity} />
          </div>
          <h4 className="text-sm font-semibold text-slate-100 font-mono">{alert.title}</h4>
        </div>
        <StatusBadge type="risk" value={alert.risk_score} />
      </div>

      <p className="text-xs text-slate-400 font-mono leading-relaxed line-clamp-2">
        {alert.summary}
      </p>

      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 pt-3 border-t border-slate-850">
        <div>
          <span className="text-slate-500">Account:</span> {alert.account_id}
        </div>
        <div>
          <span className="text-slate-500">Txn:</span> {alert.transaction_id}
        </div>
      </div>

      <div className="flex items-center justify-between pt-2">
        <Link
          href={`/alerts/${alert.id}`}
          className="text-xs font-mono text-slate-400 hover:text-slate-200 transition"
        >
          View Details &rarr;
        </Link>

        {onInvestigate && (
          <button
            onClick={() => onInvestigate(alert.id)}
            disabled={isInvestigating}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white transition shadow-sm shadow-sky-600/30"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>{isInvestigating ? 'Triage...' : 'Start Investigation'}</span>
          </button>
        )}
      </div>
    </div>
  );
}
