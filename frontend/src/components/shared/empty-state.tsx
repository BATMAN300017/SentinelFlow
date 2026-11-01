'use client';

import React from 'react';
import { Database, Search } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: 'search' | 'database';
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  title = 'No Records Found',
  description = 'There are no items matching the selected parameters.',
  icon = 'database',
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="py-12 px-4 text-center flex flex-col items-center justify-center space-y-3">
      <div className="p-3 rounded-xl bg-slate-800/80 text-slate-400 border border-slate-700/60">
        {icon === 'search' ? <Search className="w-6 h-6" /> : <Database className="w-6 h-6" />}
      </div>
      <h4 className="text-sm font-semibold text-slate-300 font-mono">{title}</h4>
      <p className="text-xs text-slate-500 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
