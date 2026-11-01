'use client';

import React from 'react';
import { Transaction } from '@/types/transaction';
import { DataTable, Column } from '@/components/shared/data-table';
import { StatusBadge } from '@/components/shared/status-badge';
import Link from 'next/link';

interface TransactionTableProps {
  transactions: Transaction[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onSelectTransaction?: (tx: Transaction) => void;
}

export function TransactionTable({
  transactions,
  loading,
  error,
  onRetry,
  onSelectTransaction,
}: TransactionTableProps) {
  const columns: Column<Transaction>[] = [
    {
      key: 'id',
      header: 'Txn ID',
      render: (tx) => (
        <span className="font-bold text-sky-400 hover:text-sky-300">
          {tx.id}
        </span>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (tx) => (
        <div className="font-bold text-slate-100">
          {tx.currency} {Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </div>
      ),
    },
    {
      key: 'source_account_id',
      header: 'Counterparties',
      render: (tx) => (
        <div className="text-[11px] text-slate-400">
          <span className="text-slate-300">{tx.source_account_id}</span> &rarr;{' '}
          <span className="text-slate-300">{tx.destination_account_id || 'EXTERNAL'}</span>
        </div>
      ),
    },
    {
      key: 'payment_channel',
      header: 'Channel',
      render: (tx) => <StatusBadge type="channel" value={tx.payment_channel} />,
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (tx) => <StatusBadge type="risk" value={tx.risk_score} />,
    },
    {
      key: 'created_at',
      header: 'Timestamp',
      render: (tx) => (
        <span className="text-[11px] text-slate-500">
          {new Date(tx.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={transactions}
      loading={loading}
      error={error}
      onRetry={onRetry}
      emptyTitle="No Transactions Located"
      emptyDescription="No events match the specified channel or risk filters."
      onRowClick={onSelectTransaction}
      keyExtractor={(tx) => tx.id}
    />
  );
}
