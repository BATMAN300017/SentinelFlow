'use client';

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  status?: number;
}

export function ErrorState({
  title = 'API Communication Interrupted',
  message = 'Failed to retrieve telemetry from backend service.',
  onRetry,
  status,
}: ErrorStateProps) {
  return (
    <div className="p-6 rounded-xl bg-rose-950/30 border border-rose-800/60 text-slate-200 space-y-4 my-4 max-w-2xl mx-auto shadow-lg backdrop-blur-sm">
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-lg bg-rose-900/50 text-rose-400 border border-rose-700/50 shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-semibold text-rose-300 font-mono">{title}</h3>
            {status && (
              <span className="text-xs px-2 py-0.5 rounded bg-rose-900/80 text-rose-300 font-mono border border-rose-700">
                HTTP {status}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 font-mono leading-relaxed">{message}</p>
        </div>
      </div>

      {onRetry && (
        <div className="flex justify-end pt-2">
          <button
            onClick={onRetry}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-800/40 hover:bg-rose-850 text-rose-200 border border-rose-700/60 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}
    </div>
  );
}
