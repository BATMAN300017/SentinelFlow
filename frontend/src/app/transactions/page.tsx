'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { TransactionTable } from '@/components/transactions/transaction-table';
import { TransactionFilters } from '@/components/transactions/transaction-filters';
import { TransactionDetail } from '@/components/transactions/transaction-detail';
import { Transaction } from '@/types/transaction';
import { fetchApi } from '@/lib/api-client';
import { ArrowLeftRight, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [channel, setChannel] = useState('');
  const [minScore, setMinScore] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('page', page.toString());
      q.set('page_size', pageSize.toString());
      if (search.trim()) q.set('search', search.trim());
      if (channel) q.set('channel', channel);
      if (minScore) q.set('min_score', minScore);

      const res = await fetchApi<any>(`/transactions?${q.toString()}`);
      setTransactions(res.items || res.transactions || []);
      if (res.total !== undefined) setTotalCount(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve transactions ledger.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, channel, minScore]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  const handleReset = () => {
    setSearch('');
    setChannel('');
    setMinScore('');
    setPage(1);
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Live Transactions Ledger</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-sky-950/80 text-sky-400 border border-sky-800">
                Calibrated Surveillance
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Real-time payment streams with deterministic rules and statistical scoring.
            </p>
          </div>

          <button
            onClick={loadTransactions}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Ledger</span>
          </button>
        </div>

        {/* Filter Controls */}
        <TransactionFilters
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setPage(1);
          }}
          channel={channel}
          onChannelChange={(val) => {
            setChannel(val);
            setPage(1);
          }}
          minScore={minScore}
          onMinScoreChange={(val) => {
            setMinScore(val);
            setPage(1);
          }}
          onReset={handleReset}
        />

        {/* Transactions Data Table */}
        <TransactionTable
          transactions={transactions}
          loading={loading}
          error={error}
          onRetry={loadTransactions}
          onSelectTransaction={(tx) => setSelectedTxn(tx)}
        />

        {/* Pagination Bar */}
        <div className="flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-xs font-mono text-slate-400">
          <span>
            Showing Page <strong className="text-slate-200">{page}</strong> (50 items/page)
            {totalCount !== null && ` • ${totalCount.toLocaleString()} total`}
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="flex items-center space-x-1 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={transactions.length < pageSize || loading}
              className="flex items-center space-x-1 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Slide-out Transaction Detail Drawer */}
        <TransactionDetail transaction={selectedTxn} onClose={() => setSelectedTxn(null)} />
      </div>
    </AppShell>
  );
}
