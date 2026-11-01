'use client';

import React from 'react';
import { Transaction } from '@/types/transaction';
import { StatusBadge } from '@/components/shared/status-badge';
import { X, ExternalLink, ShieldCheck, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface TransactionDetailProps {
  transaction: Transaction | null;
  onClose: () => void;
}

export function TransactionDetail({ transaction, onClose }: TransactionDetailProps) {
  if (!transaction) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-slate-900 border-l border-slate-800 p-6 shadow-2xl overflow-y-auto space-y-6 animate-slide-in">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="text-xs font-mono font-bold text-sky-400">{transaction.id}</span>
          <h3 className="text-sm font-bold font-mono text-slate-100">Transaction Telemetry</h3>
        </div>
        <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-slate-200">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase text-slate-500">Gross Settlement</div>
          <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">
            {transaction.currency}{' '}
            {Number(transaction.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <StatusBadge type="risk" value={transaction.risk_score} />
      </div>

      <div className="space-y-3 text-xs font-mono">
        <div className="space-y-1">
          <span className="text-slate-500">Source Account</span>
          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-200 flex items-center justify-between">
            <span>{transaction.source_account_id}</span>
            <Link
              href={`/entities/${transaction.source_account_id}`}
              className="text-sky-400 hover:text-sky-300"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-slate-500">Destination Account</span>
          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-200 flex items-center justify-between">
            <span>{transaction.destination_account_id || 'EXTERNAL_BENEFICIARY'}</span>
            {transaction.destination_account_id && (
              <Link
                href={`/entities/${transaction.destination_account_id}`}
                className="text-sky-400 hover:text-sky-300"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-500 text-[10px]">Payment Channel</span>
            <div className="font-bold text-slate-200 mt-1">{transaction.payment_channel}</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-500 text-[10px]">Settlement Status</span>
            <div className="font-bold text-emerald-400 mt-1">{transaction.status}</div>
          </div>
        </div>
      </div>

      {transaction.anomaly_reasons && transaction.anomaly_reasons.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-mono font-semibold text-slate-300">Flagged Anomaly Flags</span>
          <div className="space-y-1.5">
            {transaction.anomaly_reasons.map((r, i) => (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-900/60 text-[11px] font-mono text-rose-300"
              >
                {r}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="pt-4 border-t border-slate-800 flex justify-end">
        <Link
          href={`/transactions/${transaction.id}`}
          className="flex items-center space-x-1.5 text-xs font-mono font-bold text-sky-400 hover:text-sky-300"
        >
          <span>Open Full Transaction Audit</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
