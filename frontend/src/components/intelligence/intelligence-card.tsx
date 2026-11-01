'use client';

import React from 'react';
import { BrainCircuit, CheckCircle, Cpu } from 'lucide-react';

interface IntelligenceCardProps {
  modelName: string;
  version: string;
  accuracy: number;
  f1Score: number;
  status?: string;
  samples?: number;
}

export function IntelligenceCard({
  modelName,
  version,
  accuracy,
  f1Score,
  status = 'EVALUATED',
  samples = 482810,
}: IntelligenceCardProps) {
  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-purple-950/80 border border-purple-800 text-purple-400">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold font-mono text-slate-100">{modelName}</h4>
            <span className="text-[11px] font-mono text-slate-500">v{version} • Multi-Signal Ensemble</span>
          </div>
        </div>

        <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800">
          {status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-2">
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
          <span className="text-slate-500 text-[10px]">Evaluation Accuracy</span>
          <div className="text-xl font-bold text-slate-100 mt-1">{(accuracy * 100).toFixed(1)}%</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
          <span className="text-slate-500 text-[10px]">F1 Diagnostic Score</span>
          <div className="text-xl font-bold text-sky-400 mt-1">{(f1Score * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="text-[11px] font-mono text-slate-500 border-t border-slate-850 pt-2 flex justify-between">
        <span>Evaluated on {samples.toLocaleString()} genuine records</span>
        <span className="text-slate-400">Isolated Test Split</span>
      </div>
    </div>
  );
}
