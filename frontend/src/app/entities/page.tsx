'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { SearchInput } from '@/components/shared/search-input';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { Users, ExternalLink, RefreshCw } from 'lucide-react';

export default function EntitiesPage() {
  const [entities, setEntities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const loadEntities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any[]>('/entities');
      setEntities(res || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve entity profiles.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEntities();
  }, [loadEntities]);

  const filtered = entities.filter((e) =>
    (e.label || e.identifier || e.id || '').toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    document.title = 'Entity Profiles & Risk Intelligence | SentinelFlow AI';
  }, []);

  return (
    <AppShell>
      <head>
        <title>Entity Profiles &amp; Risk Intelligence | SentinelFlow AI</title>
        <meta name="description" content="Continuous counterparty risk profiling, customer baseline behaviors, and entity surveillance telemetry." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Entity & Account Profiles</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-sky-950/80 text-sky-400 border border-sky-800">
                Persistent Graph Store
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Know Your Customer (KYC), account centrality, risk exposure, and counterparties.
            </p>
          </div>

          <button
            onClick={loadEntities}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Entities</span>
          </button>
        </div>

        <div className="w-full sm:w-80">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search account identifier or label..."
          />
        </div>

        {loading ? (
          <LoadingState message="Loading account risk profiles..." rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadEntities} />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((e) => (
              <div
                key={e.id}
                className="p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-3 hover:border-slate-700 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-mono font-bold text-sky-400">{e.identifier || e.id}</span>
                    <h3 className="text-sm font-semibold font-mono text-slate-100">{e.label || 'Account Profile'}</h3>
                  </div>
                  <StatusBadge type="severity" value={e.risk_level || 'ROUTINE'} />
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-850">
                  <div>
                    <span className="text-slate-500">Type:</span> {e.type || 'ACCOUNT'}
                  </div>
                  <div>
                    <span className="text-slate-500">Risk Score:</span>{' '}
                    <span className="text-slate-200 font-bold">{e.risk_score || 18}/100</span>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Link
                    href={`/entities/${e.id}`}
                    className="flex items-center space-x-1 text-xs font-mono font-bold text-sky-400 hover:text-sky-300"
                  >
                    <span>View Dossier</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
