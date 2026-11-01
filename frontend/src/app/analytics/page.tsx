'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { RiskDistributionChart } from '@/components/dashboard/risk-distribution-chart';
import { TransactionVolumeChart } from '@/components/dashboard/transaction-volume-chart';
import { AlertTrendChart } from '@/components/dashboard/alert-trend-chart';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { BarChart3, RefreshCw } from 'lucide-react';

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any>('/dashboard/trends');
      setTrends(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Telemetry & Fraud Analytics</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-sky-950/80 text-sky-400 border border-sky-800">
                Calibrated Portfolio
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Statistical risk bands, transaction throughput velocities, and alert density curves.
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Analytics</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Calculating portfolio risk distribution..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RiskDistributionChart distribution={trends?.risk_score_distribution} />
              <TransactionVolumeChart />
            </div>

            <AlertTrendChart />
          </div>
        )}
      </div>
    </AppShell>
  );
}
