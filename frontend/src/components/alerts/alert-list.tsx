'use client';

import React from 'react';
import { Alert } from '@/types/index';
import { DataTable, Column } from '@/components/shared/data-table';
import { StatusBadge } from '@/components/shared/status-badge';
import Link from 'next/link';

interface AlertListProps {
  alerts: Alert[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onInvestigate?: (alertId: string) => void;
  investigatingId?: string | null;
}

export function AlertList({
  alerts,
  loading,
  error,
  onRetry,
  onInvestigate,
  investigatingId,
}: AlertListProps) {
  const columns: Column<Alert>[] = [
    {
      key: 'alert_ref',
      header: 'Reference',
      render: (a) => (
        <Link href={`/alerts?id=${a.id}`} className="font-bold text-sky-400 hover:text-sky-300">
          {a.alert_ref}
        </Link>
      ),
    },
    {
      key: 'title',
      header: 'Incident Title',
      render: (a) => (
        <div>
          <div className="font-semibold text-slate-200 line-clamp-1">{a.title}</div>
          <div className="text-[10px] text-slate-500 line-clamp-1">{a.summary}</div>
        </div>
      ),
    },
    {
      key: 'account_id',
      header: 'Target Account',
      render: (a) => <span className="text-slate-300">{a.account_id}</span>,
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (a) => <StatusBadge type="severity" value={a.severity} />,
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (a) => <StatusBadge type="risk" value={a.risk_score} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (a) => <StatusBadge type="case_status" value={a.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => (
        <div className="flex items-center space-x-2">
          {onInvestigate && (
            <button
              onClick={() => onInvestigate(a.id)}
              disabled={investigatingId === a.id}
              className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-sky-600/30 hover:bg-sky-600 text-sky-300 hover:text-white border border-sky-500/40 transition"
            >
              {investigatingId === a.id ? 'Investigating...' : 'Triage Case'}
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={alerts}
      loading={loading}
      error={error}
      onRetry={onRetry}
      emptyTitle="No Alerts Active"
      emptyDescription="All incoming transactions are within routine statistical thresholds."
      keyExtractor={(a) => a.id}
    />
  );
}
