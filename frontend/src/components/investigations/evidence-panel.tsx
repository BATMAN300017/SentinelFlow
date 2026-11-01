'use client';

import React from 'react';
import { EvidenceItem } from '@/types/investigation';
import { FileCheck, Shield, GitCommit, Database, Laptop } from 'lucide-react';

interface EvidencePanelProps {
  evidence?: EvidenceItem[];
  accountsInvolved?: string[];
}

export function EvidencePanel({ evidence = [], accountsInvolved = [] }: EvidencePanelProps) {
  const defaultEvidence: EvidenceItem[] = evidence.length > 0 ? evidence : [
    {
      id: 'EVD-001',
      investigation_id: 'active',
      evidence_type: 'TRANSACTION',
      reference_id: 'TXN-RAPID-FWD-894',
      description: 'Rapid inbound/outbound transfer structured < 180s between source and intermediary mule node.',
      confidence_score: 94,
      added_at: new Date().toISOString(),
    },
    {
      id: 'EVD-002',
      investigation_id: 'active',
      evidence_type: 'GRAPH_CYCLE',
      reference_id: 'CYCLE-3HOP-MULE',
      description: 'Circular fund flow identified returning 88% of principal back to originator account via layered shell.',
      confidence_score: 89,
      added_at: new Date().toISOString(),
    },
    {
      id: 'EVD-003',
      investigation_id: 'active',
      evidence_type: 'IP_LOG',
      reference_id: 'IP-ANOMALY-ASN',
      description: 'Velocity spike from high-risk hosting ASN with rotating Tor exit node signatures.',
      confidence_score: 82,
      added_at: new Date().toISOString(),
    },
  ];

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-100 font-mono">
          Corroborated Evidentiary Artifacts
        </h3>
        <span className="text-xs font-mono text-sky-400">
          {defaultEvidence.length} items logged
        </span>
      </div>

      <div className="space-y-3">
        {defaultEvidence.map((ev) => (
          <div
            key={ev.id}
            className="p-4 rounded-xl border border-slate-850 bg-slate-950/60 space-y-2 hover:border-slate-700 transition"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-sky-400">{ev.reference_id}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {ev.evidence_type}
                </span>
              </div>
              <span className="text-xs font-mono font-bold text-emerald-400">
                {ev.confidence_score}% Confidence
              </span>
            </div>

            <p className="text-xs font-mono text-slate-300 leading-relaxed">{ev.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
