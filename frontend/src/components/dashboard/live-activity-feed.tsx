'use client';

import React from 'react';
import { Transaction } from '@/types/transaction';
import { StatusBadge } from '@/components/shared/status-badge';
import Link from 'next/link';
import { Activity, ArrowRight } from 'lucide-react';

interface LiveActivityFeedProps {
  transactions?: Transaction[];
}

export function LiveActivityFeed({ transactions = [] }: LiveActivityFeedProps) {
  return (
    <div className="p-4 sm:p-5 rounded-lg border border-slate-800/80 bg-[#111722] space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-semibold text-slate-100 font-mono uppercase tracking-wider">
            Real-Time Surveillance Feed
          </h3>
        </div>
        <Link
          href="/transactions"
          className="text-xs font-mono text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
        >
          <span>All Stream</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-1.5">
        {transactions.slice(0, 6).map((tx) => (
          <Link
            key={tx.id}
            href={`/transactions?id=${tx.id}`}
            className="p-2.5 rounded-md border border-slate-800/80 bg-[#0B0F17] hover:bg-slate-900/90 hover:border-slate-700 transition-colors flex items-center justify-between text-xs font-mono group block"
          >
            <div className="space-y-0.5 min-w-0 pr-2">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-200 group-hover:text-emerald-400 transition-colors truncate">{tx.id}</span>
                <StatusBadge type="channel" value={tx.payment_channel} />
              </div>
              <div className="text-[10px] text-slate-500 truncate">
                {tx.source_account_id} &rarr; {tx.destination_account_id || 'EXTERNAL'}
              </div>
            </div>

            <div className="text-right space-y-1 shrink-0">
              <div className="font-bold text-slate-200 tabular-nums text-xs">
                {tx.currency} {Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <StatusBadge type="risk" value={tx.risk_score} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
