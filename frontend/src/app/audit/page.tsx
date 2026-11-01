'use client';

import React, { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { ScrollText, RefreshCw, ShieldCheck, X, Filter } from 'lucide-react';
import Link from 'next/link';

function AuditContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const resourceIdParam = searchParams.get('resource_id');
  const resourceTypeParam = searchParams.get('resource_type');

  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  const loadAudit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('page_size', '50');
      if (resourceIdParam) q.set('resource_id', resourceIdParam);
      if (resourceTypeParam) q.set('resource_type', resourceTypeParam);

      const res = await fetchApi<any>(`/audit?${q.toString()}`);
      setAudit(res.items || []);
      if (res.total !== undefined) setTotalCount(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve immutable audit trail.');
    } finally {
      setLoading(false);
    }
  }, [resourceIdParam, resourceTypeParam]);

  useEffect(() => {
    document.title = resourceIdParam
      ? `Audit Trail (${resourceIdParam}) | SentinelFlow AI`
      : 'Audit Trail & Compliance Ledger | SentinelFlow AI';
    loadAudit();
  }, [loadAudit, resourceIdParam]);

  return (
    <AppShell>
      <head>
        <title>{resourceIdParam ? `Audit Trail (${resourceIdParam}) | SentinelFlow AI` : 'Audit Trail & Compliance Ledger | SentinelFlow AI'}</title>
        <meta name="description" content="Immutable compliance audit logs, case disposition histories, analyst interventions, and evidentiary verification." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-emerald-950/40 pb-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="p-2 rounded-xl bg-emerald-950/80 border border-emerald-800/80 text-emerald-400">
                <ScrollText className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
                  <span>Immutable Audit Trail</span>
                  <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                    Cryptographic Integrity
                  </span>
                </h1>
                <p className="text-xs sm:text-sm text-slate-400 font-mono mt-0.5">
                  Tamper-evident logs of investigator actions, disposition submissions, and model promotion changes.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadAudit}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Sync Audit Log</span>
            </button>
          </div>
        </div>

        {/* Active Resource Filter Banner */}
        {resourceIdParam && (
          <div className="p-3 bg-emerald-950/60 border border-emerald-800/80 rounded-xl flex items-center justify-between text-xs font-mono">
            <div className="flex items-center space-x-2 text-emerald-300">
              <Filter className="w-4 h-4 text-emerald-400" />
              <span>
                Filtered by Resource ID:{' '}
                <strong className="text-white bg-slate-900 px-2 py-0.5 rounded border border-emerald-700">
                  {resourceIdParam}
                </strong>
                {resourceTypeParam && ` (Type: ${resourceTypeParam})`}
              </span>
            </div>
            <button
              onClick={() => router.push('/audit')}
              className="flex items-center space-x-1 text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-900 border border-slate-700"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear Filter</span>
            </button>
          </div>
        )}

        {loading ? (
          <LoadingState message="Verifying audit log integrity hashes and signatures..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadAudit} />
        ) : (
          <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl backdrop-blur-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/90 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-5 py-3.5">Timestamp (UTC)</th>
                  <th className="px-5 py-3.5">Actor / Subject</th>
                  <th className="px-5 py-3.5">Action Executed</th>
                  <th className="px-5 py-3.5">Target Resource</th>
                  <th className="px-5 py-3.5">Payload & Context</th>
                  <th className="px-5 py-3.5">Integrity Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {audit.length > 0 ? (
                  audit.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-5 py-3.5 text-slate-400 whitespace-nowrap">
                        {new Date(a.created_at || Date.now()).toISOString().replace('T', ' ').substring(0, 19)}
                      </td>
                      <td className="px-5 py-3.5 font-bold text-slate-200">
                        {a.actor_name || 'System Pipeline'}
                      </td>
                      <td className="px-5 py-3.5 text-sky-400 font-bold">
                        <span className="px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-[10px]">
                          {a.action}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-slate-300 font-bold">
                        {a.resource_type}:{a.resource_id}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 max-w-xs truncate" title={JSON.stringify(a.metadata || {})}>
                        {JSON.stringify(a.metadata || {})}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500 font-mono text-[10px]">
                        {String(a.id).substring(0, 16)}...
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500">
                      {resourceIdParam ? `No audit events logged for resource ${resourceIdParam}.` : 'No audit events recorded yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function AuditPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading immutable audit trail..." />}>
      <AuditContent />
    </Suspense>
  );
}
