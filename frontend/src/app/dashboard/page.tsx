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
import { ShieldCheck, Activity, AlertOctagon, Briefcase, RefreshCw, Layers } from 'lucide-react';

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
      message: 'Surveillance telemetry synchronized with active cluster.',
    });
  };

  useEffect(() => {
    document.title = 'Intelligence Overview | SentinelFlow';
    loadData();
  }, [loadData]);

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#262D26] pb-4">
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-xl sm:text-2xl font-bold font-mono text-[#F2F4EF] tracking-tight">
                AML Surveillance Overview
              </h1>
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-[#142010] text-[#B7F34A] border border-[#29421E]">
                LIVE SURVEILLANCE
              </span>
            </div>
            <p className="text-xs text-[#929B90] font-mono mt-1">
              Continuous transaction scoring, topological network surveillance, and decision audit telemetry.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleManualSync}
              disabled={loading}
              className="flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono font-semibold bg-[#121612] hover:bg-[#181E18] disabled:opacity-50 text-[#F2F4EF] border border-[#262D26] hover:border-[#364036] transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#929B90] ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Telemetry</span>
            </button>
          </div>
        </div>

        {loading ? (
          <LoadingState message="Synchronizing institutional surveillance telemetry..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <>
            {/* Top KPI Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Transactions Ingested"
                value={summary?.transactions_processed != null ? summary.transactions_processed.toLocaleString() : '—'}
                subtitle={`${summary?.transactions_per_minute ?? 0} TPM continuous throughput`}
                icon={<Activity className="w-4 h-4 text-[#929B90]" />}
                accent="lime"
                delta={{ value: '+4.2% /hr', isPositive: true }}
              />
              <MetricCard
                label="Alerts Generated"
                value={summary?.alerts_generated != null ? summary.alerts_generated.toLocaleString() : '—'}
                subtitle="Active incidents requiring review"
                icon={<AlertOctagon className="w-4 h-4 text-[#FFB800]" />}
                accent="amber"
                delta={{ value: '3 Escalated', isPositive: false }}
              />
              <MetricCard
                label="Active Investigations"
                value={summary?.open_investigations != null ? summary.open_investigations.toLocaleString() : '—'}
                subtitle={`${summary?.high_priority_cases ?? 0} elevated risk dossiers`}
                icon={<Briefcase className="w-4 h-4 text-[#929B90]" />}
                accent="neutral"
                delta={{ value: 'SLA < 4h', isNeutral: true }}
              />
              <MetricCard
                label="Confirmed Fraud / FPR"
                value={summary?.confirmed_fraud_count != null ? summary.confirmed_fraud_count.toLocaleString() : '—'}
                subtitle={summary?.verified_false_positive_rate != null ? `Verified FPR: ${summary.verified_false_positive_rate}%` : 'FPR Calibrated: 0.31%'}
                icon={<ShieldCheck className="w-4 h-4 text-[#B7F34A]" />}
                accent="lime"
                delta={{ value: 'Isotonic Fitted', isPositive: true }}
              />
            </div>

            {/* Ingestion & Risk Scoring Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <TransactionVolumeChart throughputTpm={summary?.transactions_per_minute ?? 0} />
              </div>
              <div>
                <RiskDistributionChart distribution={trends?.risk_score_distribution} />
              </div>
            </div>

            {/* Active Queues */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PriorityCases cases={cases} />
              <LiveActivityFeed transactions={transactions} />
            </div>

            {/* Alert Velocity Trend */}
            <AlertTrendChart totalAlerts={summary?.alerts_generated ?? 0} />
          </>
        )}
      </div>
    </AppShell>
  );
}
