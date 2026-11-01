'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '@/lib/api-client';
import { DashboardSummary, DashboardTrends } from '@/types/analytics';

export function useDashboardMetrics(refreshIntervalMs = 15000) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<DashboardTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [sumRes, trendRes] = await Promise.all([
        fetchApi<DashboardSummary>('/dashboard/summary'),
        fetchApi<DashboardTrends>('/dashboard/trends').catch(() => ({ risk_score_distribution: [] })),
      ]);
      setSummary(sumRes);
      setTrends(trendRes);
      setError(null);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    if (refreshIntervalMs > 0) {
      const timer = setInterval(loadData, refreshIntervalMs);
      return () => clearInterval(timer);
    }
  }, [loadData, refreshIntervalMs]);

  return { summary, trends, loading, error, reload: loadData, lastUpdated };
}
