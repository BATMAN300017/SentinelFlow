'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { RiskBreakdown } from '@/components/transactions/risk-breakdown';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, ExternalLink } from 'lucide-react';

export default function TransactionDetailPageClient() {
  const params = useParams();
  const txnId = params?.id as string;
  const [txn, setTxn] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!txnId) return;
      setLoading(true);
      setError(null);
      try {
        const t = await fetchApi<any>(`/transactions/${txnId}`);
        setTxn(t);
        const r = await fetchApi<any>(`/transactions/${txnId}/risk`).catch(() => null);
        setRisk(r);
      } catch (e: any) {
        setError(e.message || `Failed to load transaction ${txnId}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [txnId]);

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <Link
            href="/transactions"
            className="flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Transactions Ledger</span>
          </Link>
          {txn && (
            <span className="font-mono text-xs font-bold text-sky-400 bg-sky-950/80 px-2.5 py-1 rounded border border-sky-800">
              {txn.id}
            </span>
          )}
        </div>

        {loading ? (
          <LoadingState message="Loading transaction audit details..." rows={6} />
        ) : error || !txn ? (
          <ErrorState
            title="Transaction Not Found"
            message={error || `Transaction ${txnId} could not be located in the database.`}
            onRetry={() => window.location.reload()}
          />
        ) : (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-sky-400">{txn.id}</span>
                  <div className="text-3xl font-bold font-mono text-slate-100 mt-1">
                    {txn.currency}{' '}
                    {Number(txn.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <StatusBadge type="risk" value={txn.risk_score} />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono pt-4 border-t border-slate-850">
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
                  <span className="text-slate-500 text-[10px]">Source Account</span>
                  <div className="text-slate-200 font-bold flex items-center justify-between">
                    <span>{txn.source_account_id}</span>
                    <Link href={`/entities/${txn.source_account_id}`} className="text-sky-400 hover:text-sky-300">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
                  <span className="text-slate-500 text-[10px]">Destination Counterparty</span>
                  <div className="text-slate-200 font-bold flex items-center justify-between">
                    <span>{txn.destination_account_id || 'EXTERNAL_BENEFICIARY'}</span>
                    {txn.destination_account_id && (
                      <Link href={`/entities/${txn.destination_account_id}`} className="text-sky-400 hover:text-sky-300">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono pt-2">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Payment Channel</span>
                  <div className="font-bold text-slate-200 mt-0.5">{txn.payment_channel}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Settlement Status</span>
                  <div className="font-bold text-emerald-400 mt-0.5">{txn.status}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Customer Ref</span>
                  <div className="font-bold text-slate-300 mt-0.5">{txn.customer_id}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Timestamp</span>
                  <div className="text-slate-400 mt-0.5">
                    {new Date(txn.created_at || Date.now()).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>

            <RiskBreakdown score={txn.risk_score} />
          </div>
        )}
      </div>
    </AppShell>
  );
}
