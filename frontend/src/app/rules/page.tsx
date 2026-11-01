'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { FileCode2, RefreshCw, ShieldCheck } from 'lucide-react';

export default function RulesPage() {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any[]>('/rules');
      setRules(res || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve detection rules.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    document.title = 'Detection Rules & Thresholds | SentinelFlow AI';
    loadRules();
  }, [loadRules]);

  return (
    <AppShell>
      <head>
        <title>Detection Rules &amp; Thresholds | SentinelFlow AI</title>
        <meta name="description" content="Configured deterministic heuristics, velocity windows, and policy thresholds for real-time fraud prevention." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Deterministic Detection Rules</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-sky-950/80 text-sky-400 border border-sky-800">
                Rule Engine
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Active regulatory heuristics, velocity boundaries, and multi-currency thresholds.
            </p>
          </div>

          <button
            onClick={loadRules}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Rules</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Loading deterministic rules..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadRules} />
        ) : (
          <div className="bg-slate-900/80 rounded-2xl border border-slate-800 overflow-hidden shadow-xl backdrop-blur-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-5 py-3.5">Rule Code</th>
                  <th className="px-5 py-3.5">Rule Description</th>
                  <th className="px-5 py-3.5">Severity</th>
                  <th className="px-5 py-3.5">Threshold Parameters</th>
                  <th className="px-5 py-3.5">Revision</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {rules.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-5 py-3.5 font-bold text-sky-400">{r.rule_code}</td>
                    <td className="px-5 py-3.5 text-slate-200">
                      <div>{r.name}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{r.description}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge type="severity" value={r.severity} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 max-w-xs truncate">
                      {typeof r.thresholds === 'object'
                        ? JSON.stringify(r.thresholds)
                        : String(r.thresholds)}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">v{r.version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
