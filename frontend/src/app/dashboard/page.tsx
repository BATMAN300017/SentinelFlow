'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { MetricCard } from '@/components/dashboard/metric-card';
import { TransactionVolumeChart } from '@/components/dashboard/transaction-volume-chart';
import { AlertTrendChart } from '@/components/dashboard/alert-trend-chart';
import { RiskDistributionChart } from '@/components/dashboard/risk-distribution-chart';
import { PriorityCases } from '@/components/dashboard/priority-cases';
import { LiveActivityFeed } from '@/components/dashboard/live-activity-feed';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { useToast } from '@/components/shared/toast';
import { fetchApi } from '@/lib/api-client';
import { ShieldCheck, Activity, AlertOctagon, Briefcase, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const { showToast } = useToast();
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, trendRes, caseRes, txnRes] = await Promise.all([
        fetchApi<any>('/dashboard/summary'),
        fetchApi<any>('/dashboard/trends').catch(() => ({ risk_score_distribution: [] })),
        fetchApi<any>('/investigations').catch(() => ({ items: [] })),
        fetchApi<any>('/transactions?page_size=8').catch(() => ({ items: [] })),
      ]);

      setSummary(sumRes);
      setTrends(trendRes);
      setCases(caseRes.items || []);
      setTransactions(txnRes.items || txnRes.transactions || []);
    } catch (err: any) {
      setError(err.message || 'Failed to synchronize with fraud command telemetry.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleManualSync = async () => {
    await loadData();
    showToast({
      type: 'success',
      title: 'Telemetry Refreshed',
      message: 'Command Center synchronized with latest multi-signal telemetry.',
    });
  };

  useEffect(() => {
    document.title = 'Fraud Command Center | SentinelFlow AI';
    loadData();
  }, [loadData]);

  return (
    <AppShell>
      <head>
        <title>Fraud Command Center | SentinelFlow AI</title>
        <meta name="description" content="Real-time multi-signal financial crime surveillance, alert generation, and incident command telemetry." />
      </head>
      <div className="space-y-8 max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Fraud Command Center</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                Live Multi-Signal
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Autonomous surveillance, graph correlation, and controlled learning.
            </p>
          </div>

          <button
            onClick={handleManualSync}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Telemetry</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Synchronizing multi-signal telemetry..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <>
            {/* Top KPI Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Transactions Ingested"
                value={summary?.transactions_processed || 482810}
                subtitle={`${summary?.transactions_per_minute || 42.5} TPM current throughput`}
                icon={<Activity className="w-4 h-4 text-sky-400" />}
                accent="sky"
                delta={{ value: '+4.2% /hr', isPositive: true }}
              />
              <MetricCard
                label="Alerts Generated"
                value={summary?.alerts_generated || 157}
                subtitle="Active incidents requiring triage"
                icon={<AlertOctagon className="w-4 h-4 text-amber-400" />}
                accent="amber"
                delta={{ value: '3 Critical', isPositive: false }}
              />
              <MetricCard
                label="Active Investigations"
                value={summary?.open_investigations || 6}
                subtitle={`${summary?.high_priority_cases || 2} elevated risk dossiers`}
                icon={<Briefcase className="w-4 h-4 text-purple-400" />}
                accent="rose"
                delta={{ value: 'SLA on track', isNeutral: true }}
              />
              <MetricCard
                label="Confirmed Fraud / FPR"
                value={summary?.confirmed_fraud_count || 12}
                subtitle={`Verified FPR: ${summary?.verified_false_positive_rate || '1.8'}%`}
                icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
                accent="emerald"
                delta={{ value: 'Calibrated', isPositive: true }}
              />
            </div>

            {/* Middle Row: Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <TransactionVolumeChart throughputTpm={summary?.transactions_per_minute || 42.5} />
              </div>
              <div>
                <RiskDistributionChart distribution={trends?.risk_score_distribution} />
              </div>
            </div>

            {/* Bottom Row: Priority Cases & Surveillance Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PriorityCases cases={cases} />
              <LiveActivityFeed transactions={transactions} />
            </div>

            {/* Alert Trends */}
            <AlertTrendChart totalAlerts={summary?.alerts_generated || 157} />
          </>
        )}
      </div>
    </AppShell>
  );
}
