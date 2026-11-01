'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { LearningMetrics } from '@/components/feedback/learning-metrics';
import { OutcomeForm } from '@/components/feedback/outcome-form';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { Cpu, RefreshCw, Play, ShieldAlert } from 'lucide-react';

export default function FeedbackLearningPage() {
  const [status, setStatus] = useState<any>(null);
  const [performance, setPerformance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, perf] = await Promise.all([
        fetchApi<any>('/learning/status').catch(() => null),
        fetchApi<any>('/learning/performance').catch(() => null),
      ]);
      setStatus(st);
      setPerformance(perf);
    } catch (err: any) {
      setError(err.message || 'Failed to load model feedback telemetry.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainMsg(null);
    try {
      const res = await fetchApi<any>('/learning/retrain', { method: 'POST' });
      setRetrainMsg(res.message || 'Controlled retraining cycle executed successfully.');
      loadData();
    } catch (err: any) {
      setRetrainMsg(err.message || 'Failed to trigger model retraining.');
    } finally {
      setRetraining(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Model Learning & Feedback Loop</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                Controlled MLOps Gate
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Investigator ground-truth capture, automated candidate validation, and safe model promotion.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRetrain}
              disabled={retraining}
              className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white shadow-lg shadow-purple-600/20 transition"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{retraining ? 'Executing...' : 'Run Retraining Cycle'}</span>
            </button>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {retrainMsg && (
          <div className="p-4 rounded-xl text-xs font-mono bg-purple-950/60 border border-purple-850 text-purple-200">
            {retrainMsg}
          </div>
        )}

        {loading ? (
          <LoadingState message="Connecting to controlled model learning telemetry..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadData} />
        ) : (
          <div className="space-y-6">
            {/* Status Overview Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                  Active Production Model
                </span>
                <div className="text-base font-bold font-mono text-slate-100">
                  {status?.current_active_model || 'Calibrated 5-Model Ensemble'}
                </div>
                <div className="text-[11px] font-mono text-emerald-400">Deployed & Monitored</div>
              </div>

              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                  Training Readiness
                </span>
                <div className="text-base font-bold font-mono text-sky-400">
                  {status?.training_data_readiness || 'READY_FOR_RETRAINING'}
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  {status?.labeled_samples_count || 32} Ground-Truth Samples Logged
                </div>
              </div>

              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                  Candidate Promotion Gate
                </span>
                <div className="text-base font-bold font-mono text-slate-200">
                  {status?.candidate_model_available ? 'Candidate Verified' : 'Standard Baseline'}
                </div>
                <div className="text-[11px] font-mono text-slate-400">Requires Manual Approval</div>
              </div>
            </div>

            <LearningMetrics evaluation={performance?.overall} />

            <OutcomeForm />
          </div>
        )}
      </div>
    </AppShell>
  );
}
