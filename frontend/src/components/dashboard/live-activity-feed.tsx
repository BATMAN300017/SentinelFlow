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
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            Surveillance Stream Feed
          </h3>
        </div>
        <Link
          href="/transactions"
          className="text-xs font-mono text-sky-400 hover:text-sky-300 flex items-center space-x-1"
        >
          <span>All Transactions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-2">
        {transactions.slice(0, 6).map((tx) => (
          <div
            key={tx.id}
            className="p-3 rounded-xl border border-slate-850 bg-slate-950/40 flex items-center justify-between text-xs font-mono"
          >
            <div className="space-y-0.5">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-200">{tx.id}</span>
                <StatusBadge type="channel" value={tx.payment_channel} />
              </div>
              <div className="text-[11px] text-slate-500">
                {tx.source_account_id} &rarr; {tx.destination_account_id || 'EXTERNAL'}
              </div>
            </div>

            <div className="text-right space-y-1">
              <div className="font-bold text-slate-200">
                {tx.currency} {Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <StatusBadge type="risk" value={tx.risk_score} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
