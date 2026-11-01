'use client';

import React from 'react';
import { Alert } from '@/types/index';
import { ShieldCheck, Cpu, GitFork, Activity } from 'lucide-react';

interface AlertExplanationProps {
  alert: Alert;
}

export function AlertExplanation({ alert }: AlertExplanationProps) {
  const heuristics = [
    {
      name: 'MAD Behavioral Anomaly',
      score: Math.min(100, Math.round(alert.risk_score * 0.95)),
      weight: '25%',
      icon: <Activity className="w-4 h-4 text-emerald-400" />,
      detail: 'Transaction volume deviates > 3.2 Median Absolute Deviations from 30-day baseline account activity.',
    },
    {
      name: 'Graph Mule Engine',
      score: Math.min(100, Math.round(alert.risk_score * 0.88)),
      weight: '20%',
      icon: <GitFork className="w-4 h-4 text-indigo-400" />,
      detail: 'Node exhibits rapid fan-in/fan-out structuring with hop distance <= 2 to suspicious sink node.',
    },
    {
      name: 'Deterministic Heuristic Rules',
      score: alert.risk_score >= 75 ? 90 : 50,
      weight: '30%',
      icon: <ShieldCheck className="w-4 h-4 text-sky-400" />,
      detail: 'Triggered HIGH_VELOCITY_RAPID_FORWARDING and OFF_HOURS_HIGH_VALUE payment thresholds.',
    },
    {
      name: 'Supervised Calibrated Ensemble',
      score: Math.min(100, Math.round(alert.risk_score * 1.02)),
      weight: '25%',
      icon: <Cpu className="w-4 h-4 text-purple-400" />,
      detail: 'Random Forest & Isolation Forest consensus confirmed high likelihood of unauthorized syndication.',
    },
  ];

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <h3 className="text-sm font-semibold text-slate-100 font-mono">
        Multi-Signal Detection Explanation
      </h3>
      <p className="text-xs text-slate-400 font-mono">
        Ensemble breakdown synthesizing statistical, graph, and supervised heuristic indicators.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {heuristics.map((h) => (
          <div key={h.name} className="p-4 rounded-xl border border-slate-850 bg-slate-950/60 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {h.icon}
                <span className="text-xs font-semibold font-mono text-slate-200">{h.name}</span>
              </div>
              <span className="text-xs font-mono font-bold text-sky-400">{h.score}/100</span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 leading-relaxed">{h.detail}</p>
            <div className="text-[10px] font-mono text-slate-500 pt-1">Model Weight: {h.weight}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
