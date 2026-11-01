'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api-client';
import { formatCurrency } from '@/lib/formatters';
import Link from 'next/link';

export default function TransactionDetailPageClient() {
  const params = useParams();
  const txnId = params?.id as string;
  const [txn, setTxn] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      if (!txnId) return;
      try {
        const t = await fetchApi<any>(`/transactions/${txnId}`);
        setTxn(t);
        const r = await fetchApi<any>(`/transactions/${txnId}/risk`);
        setRisk(r);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, [txnId]);

  if (!txn) return <div className="p-8 text-center text-slate-400">Loading transaction...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <Link href="/transactions" className="text-xs text-slate-500 hover:text-slate-800">&larr; Back to Transactions</Link>
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h1 className="text-xl font-bold text-slate-900">Transaction {txn.id}</h1>
        <div className="text-2xl font-bold text-slate-900">{formatCurrency(txn.amount, txn.currency)}</div>
        <p className="text-xs text-slate-600 font-mono">Channel: {txn.payment_channel} | Status: {txn.status}</p>
        {risk && (
          <div className="mt-4 p-4 bg-slate-50 rounded-lg text-xs space-y-2">
            <div className="font-semibold text-slate-800">Risk Score: {risk.final_risk_score} ({risk.risk_band})</div>
            <div className="text-slate-600">{risk.narrative_explanation}</div>
          </div>
        )}
      </div>
    </div>
  );
}
