'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '@/lib/api-client';
import { Transaction, TransactionFilter } from '@/types/transaction';

export function useLiveTransactions(initialFilter: TransactionFilter = {}) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TransactionFilter>(initialFilter);
  const [page, setPage] = useState(initialFilter.page || 1);
  const [pageSize, setPageSize] = useState(initialFilter.page_size || 50);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      queryParams.set('page', page.toString());
      queryParams.set('page_size', pageSize.toString());

      if (filter.search) queryParams.set('search', filter.search);
      if (filter.channel) queryParams.set('channel', filter.channel);
      if (filter.min_score !== undefined) queryParams.set('min_score', filter.min_score.toString());

      const res = await fetchApi<{ items?: Transaction[]; transactions?: Transaction[]; total?: number }>(
        `/transactions?${queryParams.toString()}`
      );

      const items = res.items || res.transactions || [];
      setTransactions(items);
    } catch (err: any) {
      setError(err.message || 'Failed to load transactions');
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filter]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  return {
    transactions,
    loading,
    error,
    page,
    setPage,
    pageSize,
    setPageSize,
    filter,
    setFilter,
    reload: fetchTransactions,
  };
}
