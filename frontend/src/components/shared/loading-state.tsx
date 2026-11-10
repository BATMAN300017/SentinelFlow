'use client';

import React from 'react';
import { RefreshCw } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  rows?: number;
}

export function LoadingState({
  message = 'Retrieving real-time data from surveillance cluster...',
  rows = 4,
}: LoadingStateProps) {
  return (
    <div className="p-8 rounded bg-[#121612] border border-[#262D26] space-y-4">
      <div className="flex items-center space-x-2 text-xs font-mono text-[#929B90]">
        <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#B7F34A]" />
        <span>{message}</span>
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="h-9 rounded bg-[#181E18]/60 animate-pulse border border-[#1F261F]"
          />
        ))}
      </div>
    </div>
  );
}
