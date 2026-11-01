'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { ScrollText, RefreshCw, ShieldCheck } from 'lucide-react';

export default function AuditPage() {
  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAudit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any>('/audit?page_size=50');
      setAudit(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve immutable audit trail.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAudit();
  }, [loadAudit]);

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Immutable Audit Trail</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                Cryptographic Integrity
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Tamper-evident logs of investigator actions, disposition submissions, and model promotion changes.
            </p>
          </div>

          <button
            onClick={loadAudit}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Audit Log</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Verifying audit log integrity hashes..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadAudit} />
        ) : (
          <div className="bg-slate-900/80 rounded-2xl border border-slate-800 overflow-hidden shadow-xl backdrop-blur-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-5 py-3.5">Timestamp (UTC)</th>
                  <th className="px-5 py-3.5">Actor / Subject</th>
                  <th className="px-5 py-3.5">Action Executed</th>
                  <th className="px-5 py-3.5">Target Resource</th>
                  <th className="px-5 py-3.5">Integrity Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {audit.length > 0 ? (
                  audit.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-5 py-3.5 text-slate-400">{new Date(a.created_at || Date.now()).toISOString()}</td>
                      <td className="px-5 py-3.5 font-bold text-slate-200">{a.actor_name || 'System Pipeline'}</td>
                      <td className="px-5 py-3.5 text-sky-400 font-bold">{a.action}</td>
                      <td className="px-5 py-3.5 text-slate-300">
                        {a.resource_type}:{a.resource_id}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500 font-mono text-[10px]">
                        {a.id.substring(0, 16)}...
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No audit events recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
