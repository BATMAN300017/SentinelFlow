'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { InvestigationHeader } from '@/components/investigations/investigation-header';
import { EvidencePanel } from '@/components/investigations/evidence-panel';
import { CaseTimeline } from '@/components/investigations/case-timeline';
import { CaseNotes } from '@/components/investigations/case-notes';
import { InvestigationChecklist } from '@/components/investigations/investigation-checklist';
import { DispositionDialog } from '@/components/investigations/disposition-dialog';
import { CaseReportPreview } from '@/components/investigations/case-report-preview';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { InvestigationCase, DispositionPayload } from '@/types/investigation';

export default function InvestigationDetailPageClient() {
  const params = useParams();
  const caseId = params?.id as string;
  const [caseData, setCaseData] = useState<InvestigationCase | null>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dispositionOpen, setDispositionOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!caseId) return;
      setLoading(true);
      setError(null);
      try {
        const c = await fetchApi<InvestigationCase>(`/investigations/${caseId}`);
        setCaseData(c);
        const ev = await fetchApi<any[]>(`/investigations/${caseId}/evidence`).catch(() => []);
        setEvidence(ev || []);
      } catch (err: any) {
        setError(err.message || `Failed to retrieve case ${caseId}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [caseId]);

  const handleDispositionSubmit = async (payload: DispositionPayload) => {
    if (!caseId) return;
    const res = await fetchApi<InvestigationCase>(`/investigations/${caseId}/disposition`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setCaseData(res);
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        {loading ? (
          <LoadingState message="Retrieving evidentiary case dossier..." rows={6} />
        ) : error || !caseData ? (
          <ErrorState
            title="Dossier Unavailable"
            message={error || `Investigation record ${caseId} could not be located.`}
            onRetry={() => window.location.reload()}
          />
        ) : (
          <>
            <InvestigationHeader
              caseData={caseData}
              onOpenDisposition={() => setDispositionOpen(true)}
              onGenerateReport={() => setReportOpen(true)}
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <EvidencePanel evidence={evidence} accountsInvolved={caseData.accounts_involved} />
                <CaseTimeline />
                <CaseNotes />
              </div>

              <div className="space-y-6">
                <InvestigationChecklist />
              </div>
            </div>

            <DispositionDialog
              isOpen={dispositionOpen}
              onClose={() => setDispositionOpen(false)}
              onSubmit={handleDispositionSubmit}
              caseNumber={caseData.case_number}
            />

            <CaseReportPreview
              isOpen={reportOpen}
              onClose={() => setReportOpen(false)}
              caseData={caseData}
            />
          </>
        )}
      </div>
    </AppShell>
  );
}
