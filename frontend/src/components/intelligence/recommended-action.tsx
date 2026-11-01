'use client';

import React from 'react';
import { ShieldAlert, Lock, CheckCircle, ArrowRight } from 'lucide-react';

interface RecommendedActionProps {
  onAction?: (actionKey: string) => void;
}

export function RecommendedAction({ onAction }: RecommendedActionProps) {
  const actions = [
    {
      key: 'FREEZE_OUTBOUND',
      title: 'Emergency Outbound Sweep Freeze',
      description: 'Halt all scheduled and real-time IMPS/UPI outbound transfers immediately to prevent capital flight.',
      icon: <Lock className="w-4 h-4 text-rose-400" />,
      btnText: 'Freeze Account',
      variant: 'rose',
    },
    {
      key: 'FILE_SAR',
      title: 'Escalate to Financial Intelligence Unit (FIU)',
      description: 'Package transaction evidence and cryptographic hash into regulatory Suspicious Activity Report format.',
      icon: <ShieldAlert className="w-4 h-4 text-amber-400" />,
      btnText: 'Draft SAR Form',
      variant: 'amber',
    },
    {
      key: 'WHITELIST_EXCEPTION',
      title: 'Flag as Benign Corporate Payroll Lookalike',
      description: 'Record positive validation feedback to calibrate model and reduce future false-positive alerts.',
      icon: <CheckCircle className="w-4 h-4 text-emerald-400" />,
      btnText: 'Verify Lookalike',
      variant: 'emerald',
    },
  ];

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <h3 className="text-sm font-semibold text-slate-100 font-mono">
        Prescriptive Next-Best Actions
      </h3>

      <div className="space-y-3">
        {actions.map((act) => (
          <div
            key={act.key}
            className="p-4 rounded-xl border border-slate-850 bg-slate-950/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                {act.icon}
                <h4 className="text-xs font-bold font-mono text-slate-200">{act.title}</h4>
              </div>
              <p className="text-[11px] font-mono text-slate-400 max-w-xl leading-relaxed">
                {act.description}
              </p>
            </div>

            <button
              onClick={() => onAction && onAction(act.key)}
              className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold shrink-0 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5"
            >
              <span>{act.btnText}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
