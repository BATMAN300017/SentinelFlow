'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { IntelligenceCard } from '@/components/intelligence/intelligence-card';
import { AnalystCopilot } from '@/components/intelligence/analyst-copilot';
import { RecommendedAction } from '@/components/intelligence/recommended-action';
import { LearningMetrics } from '@/components/feedback/learning-metrics';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { BrainCircuit, RefreshCw, Database } from 'lucide-react';

export default function IntelligencePage() {
  const [performance, setPerformance] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [perfRes, dataRes] = await Promise.all([
        fetchApi<any>('/learning/performance').catch(() => null),
        fetchApi<any[]>('/datasets').catch(() => []),
      ]);
      setPerformance(perfRes);
      setDatasets(dataRes || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve model intelligence.');
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
              <span>Model Intelligence & Learning Center</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-purple-950/80 text-purple-400 border border-purple-800">
                Calibrated Ensemble
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Deterministic rules, MAD behavioral anomaly, Isolation Forest, and Random Forest consensus.
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Models</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Retrieving model weights, evaluation metrics, and dataset provenance..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <div className="space-y-6">
            <LearningMetrics evaluation={performance?.overall} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <AnalystCopilot />
              <RecommendedAction />
            </div>

            {/* Datasets Laboratory Section */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-sky-400" />
                <h3 className="text-base font-bold font-mono text-slate-100">
                  Dataset Laboratory & Provenance Store
                </h3>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Verified financial crime benchmark datasets registered with strict ground-truth label isolation.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                {datasets.map((d) => (
                  <div
                    key={d.id}
                    className="p-4 rounded-xl border border-slate-850 bg-slate-950/60 space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-sky-400">{d.id}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        v{d.version}
                      </span>
                    </div>
                    <h4 className="text-xs font-semibold font-mono text-slate-200 line-clamp-1">{d.title}</h4>
                    <div className="text-[11px] font-mono text-slate-500 pt-1">
                      Domain: <span className="text-slate-300">{d.domain}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
