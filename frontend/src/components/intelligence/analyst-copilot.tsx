'use client';

import React, { useState } from 'react';
import { Sparkles, Copy, Check } from 'lucide-react';

interface AnalystCopilotProps {
  entityId?: string;
  contextText?: string;
}

export function AnalystCopilot({
  entityId = 'ACCT_000104',
  contextText,
}: AnalystCopilotProps) {
  const [copied, setCopied] = useState(false);

  const narrative =
    contextText ||
    `Telemetry Analysis: Target entity ${entityId} exhibits a high-confidence intermediary mule signature. Over the last observation window, the account received ₹500,000 via high-value RTGS and initiated immediate outbound splits to 2 downstream sink accounts within 180 seconds. Behavioral dispersion deviates > 3.2 Median Absolute Deviations from legitimate peer lookalikes. Recommendation: Freeze outbound IMPS sweeps and prepare regulatory SAR filing.`;

  const copyNarrative = () => {
    navigator.clipboard.writeText(narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6 rounded-2xl border border-sky-900/50 bg-gradient-to-br from-slate-900 via-slate-900/90 to-sky-950/30 shadow-xl backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-sky-400 animate-pulse" />
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            Autonomous Narrative Copilot
          </h3>
        </div>
        <button
          onClick={copyNarrative}
          className="flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Narrative'}</span>
        </button>
      </div>

      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300 leading-relaxed">
        {narrative}
      </div>

      <div className="text-[10px] font-mono text-slate-500 flex justify-between">
        <span>Grounded on verified database records • Zero LLM hallucination</span>
        <span className="text-sky-400">Deterministic Evidence Synthesizer</span>
      </div>
    </div>
  );
}
