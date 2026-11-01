'use client';

import React from 'react';
import { InvestigationCase } from '@/types/investigation';
import { StatusBadge } from '@/components/shared/status-badge';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, FileText, User } from 'lucide-react';

interface InvestigationHeaderProps {
  caseData: InvestigationCase;
  onOpenDisposition?: () => void;
  onGenerateReport?: () => void;
}

export function InvestigationHeader({
  caseData,
  onOpenDisposition,
  onGenerateReport,
}: InvestigationHeaderProps) {
  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/investigations"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-sky-400">{caseData.case_number}</span>
              <StatusBadge type="severity" value={caseData.priority} />
              <StatusBadge type="case_status" value={caseData.status} />
            </div>
            <h1 className="text-xl font-bold font-mono text-slate-100 mt-1">{caseData.title}</h1>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {onGenerateReport && (
            <button
              onClick={onGenerateReport}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Export Dossier</span>
            </button>
          )}

          {onOpenDisposition && (
            <button
              onClick={onOpenDisposition}
              className="flex items-center space-x-2 px-4 py-1.5 rounded-lg text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Submit Disposition</span>
            </button>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400 font-mono leading-relaxed">{caseData.summary}</p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono text-slate-400 pt-3 border-t border-slate-850">
        <div>
          <span className="text-slate-500">Evidence Completeness:</span>{' '}
          <span className="text-sky-400 font-bold">{caseData.evidence_completeness_score}%</span>
        </div>
        <div>
          <span className="text-slate-500">Lead Analyst:</span>{' '}
          <span className="text-slate-300">{caseData.lead_analyst || 'Sarah Chen'}</span>
        </div>
        <div>
          <span className="text-slate-500">Created:</span>{' '}
          <span className="text-slate-300">{new Date(caseData.created_at).toLocaleDateString()}</span>
        </div>
        <div>
          <span className="text-slate-500">Disposition:</span>{' '}
          <span className="text-amber-400 font-bold">{caseData.disposition || 'Pending'}</span>
        </div>
      </div>
    </div>
  );
}
