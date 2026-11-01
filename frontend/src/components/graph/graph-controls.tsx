'use client';

import React from 'react';
import { ZoomIn, ZoomOut, RefreshCw, Layers } from 'lucide-react';

interface GraphControlsProps {
  hopDepth?: number;
  onHopDepthChange?: (depth: number) => void;
  onResetView?: () => void;
}

export function GraphControls({
  hopDepth = 2,
  onHopDepthChange,
  onResetView,
}: GraphControlsProps) {
  return (
    <div className="flex items-center space-x-3 p-3 rounded-xl border border-slate-800/80 bg-[#111722] shadow-md">
      <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-300">
        <Layers className="w-3.5 h-3.5 text-emerald-400" />
        <span>Hop Depth:</span>
        {[1, 2, 3].map((d) => (
          <button
            key={d}
            onClick={() => onHopDepthChange && onHopDepthChange(d)}
            className={`px-2 py-0.5 rounded text-xs font-mono font-bold transition ${
              hopDepth === d
                ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-950/30'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {onResetView && (
        <button
          onClick={onResetView}
          className="flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Reset Layout</span>
        </button>
      )}
    </div>
  );
}
