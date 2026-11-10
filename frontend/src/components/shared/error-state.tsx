'use client';

import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = 'API Communication Interrupted',
  message = 'Failed to synchronize with backend surveillance service.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="p-8 rounded bg-[#181414] border border-[#4A2020] text-center max-w-lg mx-auto">
      <div className="w-10 h-10 rounded bg-[#2A1414] border border-[#5A2020] text-[#FF4D4D] flex items-center justify-center mx-auto mb-3">
        <AlertCircle className="w-5 h-5" />
      </div>
      <h3 className="text-sm font-mono font-bold text-[#F2F4EF]">{title}</h3>
      <p className="text-xs font-mono text-[#FFA1A1] mt-1 mb-4 leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono font-semibold bg-[#261616] text-[#FFBABA] hover:bg-[#381F1F] border border-[#5A2020] transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </button>
      )}
    </div>
  );
}
