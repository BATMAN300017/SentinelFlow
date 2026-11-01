'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  rows?: number;
}

export function LoadingState({ message = 'Loading financial telemetry...', rows = 4 }: LoadingStateProps) {
  return (
    <div className="w-full py-8 px-4 flex flex-col items-center justify-center space-y-4">
      <div className="flex items-center space-x-3 text-sky-400">
        <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
        <span className="text-sm font-medium tracking-wide text-slate-300 font-mono">{message}</span>
      </div>

      <div className="w-full max-w-3xl space-y-2 mt-4 opacity-40">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-10 bg-slate-800/80 rounded-md animate-pulse border border-slate-700/40" />
        ))}
      </div>
    </div>
  );
}
