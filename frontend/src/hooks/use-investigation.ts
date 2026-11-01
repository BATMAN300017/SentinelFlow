'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '@/lib/api-client';
import { InvestigationCase, EvidenceItem, TimelineEvent, CaseNote, DispositionPayload } from '@/types/investigation';

export function useInvestigation(caseId?: string) {
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [activeCase, setActiveCase] = useState<InvestigationCase | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [notes, setNotes] = useState<CaseNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCases = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchApi<{ items?: InvestigationCase[] }>('/investigations');
      setCases(res.items || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load investigations');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCaseDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const res = await fetchApi<InvestigationCase>(`/investigations/${id}`);
      setActiveCase(res);
      setError(null);
    } catch (err: any) {
      setError(err.message || `Failed to load case ${id}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (caseId) {
      loadCaseDetail(caseId);
    } else {
      loadCases();
    }
  }, [caseId, loadCaseDetail, loadCases]);

  const submitDisposition = async (id: string, payload: DispositionPayload) => {
    const res = await fetchApi<InvestigationCase>(`/investigations/${id}/disposition`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setActiveCase(res);
    return res;
  };

  return {
    cases,
    activeCase,
    evidence,
    timeline,
    notes,
    loading,
    error,
    reload: caseId ? () => loadCaseDetail(caseId) : loadCases,
    submitDisposition,
  };
}
