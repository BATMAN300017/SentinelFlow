'use client';

import React from 'react';
import { LoadingState } from './loading-state';
import { EmptyState } from './empty-state';
import { ErrorState } from './error-state';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (item: T) => void;
  keyExtractor: (item: T) => string;
}

export function DataTable<T>({
  columns,
  data,
  loading,
  error,
  onRetry,
  emptyTitle,
  emptyDescription,
  onRowClick,
  keyExtractor,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/80 bg-[#111722] p-6">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800/80 bg-[#111722] p-6">
        <EmptyState title={emptyTitle} description={emptyDescription} />
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-[#111722] shadow-xl">
      <table className="w-full text-left text-xs">
        <thead className="bg-[#0B0F17] border-b border-slate-800/80 text-slate-400 font-mono uppercase tracking-wider text-[11px]">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={`px-4 py-3 font-semibold ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              onClick={() => onRowClick && onRowClick(item)}
              className={`transition-colors hover:bg-slate-800/30 ${
                onRowClick ? 'cursor-pointer' : ''
              }`}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-slate-300 font-mono tabular-nums ${col.className || ''}`}>
                  {col.render ? col.render(item) : (item as any)[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
