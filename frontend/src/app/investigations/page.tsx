'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { DataTable, Column } from '@/components/shared/data-table';
import { StatusBadge } from '@/components/shared/status-badge';
import { InvestigationCase } from '@/types/investigation';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { Briefcase, RefreshCw, Plus } from 'lucide-react';

export default function InvestigationsPage() {
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any>('/investigations?page_size=50');
      setCases(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve active investigations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const columns: Column<InvestigationCase>[] = [
    {
      key: 'case_number',
      header: 'Case Number',
      render: (c) => (
        <Link href={`/investigations/${c.id}`} className="font-bold font-mono text-sky-400 hover:text-sky-300">
          {c.case_number}
        </Link>
      ),
    },
    {
      key: 'title',
      header: 'Investigation Title',
      render: (c) => (
        <div>
          <div className="font-semibold text-slate-100 line-clamp-1">{c.title}</div>
          <div className="text-[10px] text-slate-500 line-clamp-1">{c.summary}</div>
        </div>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (c) => <StatusBadge type="severity" value={c.priority} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (c) => <StatusBadge type="case_status" value={c.status} />,
    },
    {
      key: 'evidence_completeness_score',
      header: 'Completeness',
      render: (c) => (
        <div className="flex items-center space-x-1.5">
          <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              style={{ width: `${c.evidence_completeness_score}%` }}
              className="h-full bg-sky-500 rounded-full"
            />
          </div>
          <span className="text-[11px] font-bold text-sky-400">{c.evidence_completeness_score}%</span>
        </div>
      ),
    },
    {
      key: 'disposition',
      header: 'Disposition',
      render: (c) => (
        <span className="font-bold text-slate-300">
          {c.disposition || 'Under Triage'}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (c) => (
        <Link
          href={`/investigations/${c.id}`}
          className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-sky-600/30 hover:bg-sky-600 text-sky-300 hover:text-white border border-sky-500/40 transition inline-block"
        >
          Open Case &rarr;
        </Link>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Investigation Workspace</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-purple-950/80 text-purple-400 border border-purple-800">
                Adjudication & Evidence
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Formal evidentiary dossiers, regulatory SAR preparations, and verified dispositions.
            </p>
          </div>

          <button
            onClick={loadCases}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Cases</span>
          </button>
        </div>

        <DataTable
          columns={columns}
          data={cases}
          loading={loading}
          error={error}
          onRetry={loadCases}
          emptyTitle="No Open Investigations"
          emptyDescription="All flagged incidents have been adjudicated or cleared."
          keyExtractor={(c) => c.id}
        />
      </div>
    </AppShell>
  );
}
