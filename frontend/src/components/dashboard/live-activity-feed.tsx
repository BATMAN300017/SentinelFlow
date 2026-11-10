'use client';

import React from 'react';
import Link from 'next/link';
import { StatusBadge } from '@/components/shared/status-badge';
import { ArrowRight } from 'lucide-react';

interface LiveActivityFeedProps {
  transactions: any[];
}

export function LiveActivityFeed({ transactions }: LiveActivityFeedProps) {
  const displayTxns = transactions && transactions.length > 0 ? transactions.slice(0, 6) : [];

  return (
    <div className="p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26] flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-[#262D26] pb-3">
          <div>
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF] flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#B7F34A]" />
              <span>Real-Time Ingestion Surveillance</span>
            </h3>
            <p className="text-[11px] text-[#687166] font-mono mt-0.5">
              Live transaction scoring stream from edge ingestion
            </p>
          </div>
          <Link
            href="/transactions"
            className="text-xs font-mono text-[#929B90] hover:text-[#B7F34A] flex items-center space-x-1 transition"
          >
            <span>Live Stream</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {displayTxns.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-[#687166]">
            Awaiting streaming transactions from message bus
          </div>
        ) : (
          <div className="divide-y divide-[#1F261F]">
            {displayTxns.map((t) => (
              <Link
                key={t.id || t.transaction_id}
                href={`/transactions/${t.id || t.transaction_id}`}
                className="py-2 flex items-center justify-between hover:bg-[#181E18] px-2 rounded -mx-2 transition group"
              >
                <div className="min-w-0 pr-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-semibold text-[#F2F4EF] group-hover:text-[#B7F34A] transition truncate">
                      {t.transaction_id || t.id}
                    </span>
                    <span className="text-[10px] font-mono px-1 rounded bg-[#0D100D] text-[#929B90] border border-[#262D26]">
                      {t.channel || 'UPI'}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#687166] font-mono truncate mt-0.5">
                    {t.sender_account || 'ACC-9812'} → {t.receiver_account || 'ACC-1402'}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-mono font-bold text-[#F2F4EF] tabular-nums">
                    ₹{(t.amount || 0).toLocaleString()}
                  </div>
                  <div className="mt-0.5">
                    <StatusBadge type="risk" value={t.risk_score || 0} showLabel={false} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-[#262D26] mt-4 flex items-center justify-between text-[11px] font-mono text-[#687166]">
        <span>Pipeline Latency: ~14ms</span>
        <span className="text-[#929B90]">Edge Ingestion: Verified</span>
      </div>
    </div>
  );
}
