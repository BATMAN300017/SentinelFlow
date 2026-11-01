'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function InvestigationDetailPageClient() {
  const params = useParams();
  const caseId = params?.id as string;
  const [caseData, setCaseData] = useState<any>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      if (!caseId) return;
      try {
        const c = await fetchApi<any>(`/investigations/${caseId}`);
        setCaseData(c);
        const ev = await fetchApi<any[]>(`/investigations/${caseId}/evidence`);
        setEvidence(ev || []);
        const t = await fetchApi<any[]>(`/investigations/${caseId}/tasks`);
        setTasks(t || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, [caseId]);

  if (!caseData) return <div className="p-8 text-center text-slate-400">Loading case dossier...</div>;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/investigations" className="text-xs text-slate-500 hover:text-slate-800">&larr; Back to Cases</Link>
        <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded border border-sky-200">{caseData.case_number}</span>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h1 className="text-xl font-bold text-slate-900">{caseData.title}</h1>
        <p className="text-xs text-slate-600">{caseData.summary}</p>
        <div className="flex space-x-4 text-xs font-medium text-slate-700 pt-2 border-t border-slate-100">
          <span>Priority: {caseData.priority}</span>
          <span>Status: {caseData.status}</span>
          <span>Completeness: {caseData.evidence_completeness_score}%</span>
          <span>Disposition: {caseData.disposition || 'Pending'}</span>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-900">Case Evidence Items ({evidence.length})</h2>
        <div className="space-y-2">
          {evidence.map(e => (
            <div key={e.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex justify-between items-start">
              <div>
                <span className="font-mono font-bold text-sky-700">[{e.evidence_type}]</span> {e.description}
                <div className="font-mono text-[10px] text-slate-400 mt-0.5">Hash: {e.integrity_hash?.substring(0, 24)}...</div>
              </div>
              <span className="font-semibold text-slate-700">{e.verification_status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
