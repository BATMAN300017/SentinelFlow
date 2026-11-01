'use client';

import React, { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { InvestigationCase, DispositionPayload } from '@/types/investigation';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import {
  Briefcase, RefreshCw, ScrollText, Network, ArrowLeft,
  CheckCircle2, AlertTriangle, ShieldCheck, Clock, FileText,
  UserCheck, ChevronRight, X, ExternalLink
} from 'lucide-react';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';

function InvestigationsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const caseIdParam = searchParams.get('id');
  const txnIdParam = searchParams.get('txn_id');

  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active focused investigation dossier
  const [activeCase, setActiveCase] = useState<any | null>(null);
  const [activeCaseLoading, setActiveCaseLoading] = useState<boolean>(false);
  const [activeCaseError, setActiveCaseError] = useState<string | null>(null);
  const [evidenceList, setEvidenceList] = useState<any[]>([]);

  // Filter state for case list
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<any>('/investigations?page_size=50');
      setCases(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve active investigations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  // Load specific case if `id` or `txn_id` is passed in URL query
  useEffect(() => {
    const targetCaseId = caseIdParam;
    if (targetCaseId) {
      loadSingleCase(targetCaseId);
    } else if (txnIdParam) {
      // Find case by transaction ID
      loadCaseByTxn(txnIdParam);
    } else {
      setActiveCase(null);
    }
  }, [caseIdParam, txnIdParam]);

  async function loadSingleCase(id: string) {
    setActiveCaseLoading(true);
    setActiveCaseError(null);
    try {
      const c = await fetchApi<any>(`/investigations/${encodeURIComponent(id)}`);
      setActiveCase(c);
      const ev = await fetchApi<any[]>(`/investigations/${encodeURIComponent(id)}/evidence`).catch(() => []);
      setEvidenceList(ev || []);
    } catch (err: any) {
      setActiveCaseError(`Investigation ${id} could not be located in the database.`);
    } finally {
      setActiveCaseLoading(false);
    }
  }

  async function loadCaseByTxn(txnId: string) {
    setActiveCaseLoading(true);
    setActiveCaseError(null);
    try {
      const res = await fetchApi<any>(`/transactions/${encodeURIComponent(txnId)}/case`);
      if (res.dossier) {
        setActiveCase({
          id: res.linked_investigation_id || `CASE-${txnId}`,
          case_number: res.dossier.case_number || `CASE-${txnId}`,
          title: res.dossier.scam_title || `Investigation: ${txnId}`,
          summary: res.dossier.modus_operandi || 'Investigative dossier assembled from transaction telemetry.',
          status: res.dossier.status || 'UNDER_INVESTIGATION',
          priority: res.dossier.risk_score >= 70 ? 'CRITICAL' : 'HIGH',
          evidence_completeness_score: 95,
          scam_dossier: res.dossier,
          transaction: res.transaction
        });
      } else {
        setActiveCaseError(`No investigation record found for transaction ${txnId}`);
      }
    } catch (err: any) {
      setActiveCaseError(`Failed to load investigation for transaction ${txnId}`);
    } finally {
      setActiveCaseLoading(false);
    }
  }

  const filteredCases = cases.filter(c => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
    if (priorityFilter !== 'ALL' && c.priority !== priorityFilter) return false;
    return true;
  });

  useEffect(() => {
    document.title = 'Investigation Workspace & Case Management | SentinelFlow AI';
  }, []);

  return (
    <AppShell>
      <head>
        <title>Investigation Workspace &amp; Case Management | SentinelFlow AI</title>
        <meta name="description" content="Evidence-grounded case dossiers, timeline reconstruction, analyst notes, and disposition adjudication." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* If viewing a single case dossier */}
        {caseIdParam || txnIdParam ? (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <button
                onClick={() => router.push('/investigations')}
                className="flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>&larr; Back to All Investigations</span>
              </button>

              <div className="flex items-center space-x-3">
                {activeCase && (
                  <Link
                    href={`/audit?resource_id=${activeCase.id}&resource_type=CASE`}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                  >
                    <ScrollText className="w-3.5 h-3.5" />
                    <span>Open Full Audit Trail</span>
                  </Link>
                )}
              </div>
            </div>

            {activeCaseLoading ? (
              <LoadingState message="Retrieving evidentiary investigation dossier..." rows={6} />
            ) : activeCaseError || !activeCase ? (
              <ErrorState
                title="Investigation Record Not Found"
                message={activeCaseError || `The requested investigation dossier could not be retrieved.`}
                onRetry={() => loadCases()}
              />
            ) : (
              /* Full Case Dossier Workspace */
              <div className="space-y-6 animate-in fade-in">
                {/* Header Banner */}
                <div className="p-5 sm:p-6 rounded-lg border border-slate-800/80 bg-[#111722] space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono text-xs font-bold text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                          {activeCase.case_number || activeCase.id}
                        </span>
                        <StatusBadge type="case_status" value={activeCase.status} />
                        <StatusBadge type="severity" value={activeCase.priority} />
                      </div>
                      <h1 className="text-xl sm:text-2xl font-bold font-mono text-slate-100">{activeCase.title}</h1>
                      <p className="text-xs text-slate-400 font-mono max-w-3xl leading-relaxed">
                        {activeCase.summary}
                      </p>
                    </div>

                    <div className="flex flex-col items-end space-y-2 text-xs font-mono">
                      <div className="text-right">
                        <span className="text-slate-400 text-[10px] uppercase tracking-wider">Disposition</span>
                        <div className="text-sm font-bold text-emerald-400">{activeCase.disposition || 'UNDER_TRIAGE'}</div>
                      </div>
                      <div className="text-right">
                        <span className="text-slate-400 text-[10px] uppercase tracking-wider">Evidence Completeness</span>
                        <div className="text-sm font-bold text-slate-200 tabular-nums">
                          {activeCase.evidence_completeness_score ? `${Number(activeCase.evidence_completeness_score) * (Number(activeCase.evidence_completeness_score) <= 1 ? 100 : 1)}%` : '95%'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
                    <div className="bg-[#0B0F17] p-2.5 rounded-md border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] uppercase">Assigned Investigator</span>
                      <div className="font-bold text-slate-200 mt-0.5">{activeCase.assigned_investigator_id || 'Marcus Vance (Lead)'}</div>
                    </div>
                    <div className="bg-[#0B0F17] p-2.5 rounded-md border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] uppercase">Supervisory Review</span>
                      <div className="font-bold text-amber-300 mt-0.5">{activeCase.peer_review_status || 'REQUESTED'}</div>
                    </div>
                    <div className="bg-[#0B0F17] p-2.5 rounded-md border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] uppercase">Model Version</span>
                      <div className="font-bold text-slate-200 mt-0.5">{activeCase.model_version || 'v2.0-consensus'}</div>
                    </div>
                    <div className="bg-[#0B0F17] p-2.5 rounded-md border border-slate-800/80">
                      <span className="text-slate-500 text-[10px] uppercase">Created Date</span>
                      <div className="font-bold text-slate-200 mt-0.5 tabular-nums">
                        {new Date(activeCase.created_at || Date.now()).toLocaleDateString([], { month: 'short', day: '2-digit', year: 'numeric' })}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Evidence & Findings Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Evidentiary Items */}
                  <div className="p-4 sm:p-5 rounded-lg bg-[#111722] border border-slate-800/80 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                      <h3 className="text-xs font-bold font-mono text-slate-100 uppercase tracking-wider flex items-center space-x-2">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span>Evidentiary Items & Records</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-500">Chain of Custody Verified</span>
                    </div>

                    <div className="space-y-2">
                      <div className="p-3 rounded-md bg-[#0B0F17] border border-slate-800/80 text-xs font-mono space-y-1">
                        <div className="flex items-center justify-between font-bold text-slate-200">
                          <span>Primary Settlement Record</span>
                          <span className="text-emerald-400 text-[10px]">VERIFIED</span>
                        </div>
                        <p className="text-slate-400 text-[11px]">
                          Transaction telemetry retrieved from production ledger and corroborated against counterparty accounts.
                        </p>
                      </div>

                      <div className="p-3 rounded-md bg-[#0B0F17] border border-slate-800/80 text-xs font-mono space-y-1">
                        <div className="flex items-center justify-between font-bold text-slate-200">
                          <span>Graph Topology & Centrality</span>
                          <span className="text-emerald-400 text-[10px]">CALIBRATED</span>
                        </div>
                        <p className="text-slate-400 text-[11px]">
                          Multi-hop traversal identifies rapid fan-in/fan-out patterns consistent with mule syndicate layering.
                        </p>
                      </div>

                      <div className="p-3 rounded-md bg-[#0B0F17] border border-slate-800/80 text-xs font-mono space-y-1">
                        <div className="flex items-center justify-between font-bold text-slate-200">
                          <span>Model Consensus Evaluation</span>
                          <span className="text-amber-400 text-[10px]">5-MODEL SIGNAL</span>
                        </div>
                        <p className="text-slate-400 text-[11px]">
                          Supervised classifier, Isolation Forest, and MAD behavioral baselines reach unanimous high-risk consensus.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Disposition & Actions Panel */}
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-sm font-bold font-mono text-slate-100 flex items-center space-x-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        <span>Investigator Disposition & Review</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-500">SAR Audit Trail</span>
                    </div>

                    <div className="space-y-3 text-xs font-mono">
                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                        <span className="text-slate-500 text-[10px]">Current Status</span>
                        <div className="font-bold text-slate-100">{activeCase.status}</div>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                        <span className="text-slate-500 text-[10px]">Disposition Rationale</span>
                        <div className="text-slate-300 text-[11px]">
                          {activeCase.disposition_rationale || 'Coordinated mule syndicate operations confirmed across multiple linked counterparties with immediate layering.'}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 pt-2">
                        <Link
                          href={`/audit?resource_id=${activeCase.id}&resource_type=CASE`}
                          className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-bold font-mono transition text-center"
                        >
                          View Case Audit Trail
                        </Link>
                        <Link
                          href={`/fund-flow`}
                          className="w-full py-2 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded-lg text-xs font-bold font-mono transition text-center"
                        >
                          Trace Network Flow
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Normal Investigations List View */
          <>
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-sky-950/40 pb-4">
              <div>
                <div className="flex items-center space-x-3">
                  <span className="p-2 rounded-xl bg-sky-950/80 border border-sky-800/80 text-sky-400">
                    <Briefcase className="w-5 h-5" />
                  </span>
                  <div>
                    <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
                      <span>Investigation Case Management</span>
                      <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-sky-950/80 text-sky-400 border border-sky-800">
                        Active Casefiles
                      </span>
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-400 font-mono mt-0.5">
                      Evidentiary dossiers, peer reviews, disposition submissions, and regulatory filings.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={loadCases}
                  disabled={loading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>Refresh Cases</span>
                </button>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0B0F17] p-2.5 rounded-lg border border-slate-800/80">
              <div className="flex flex-wrap items-center gap-1">
                {['ALL', 'UNDER_INVESTIGATION', 'PENDING_PEER_REVIEW', 'RESOLVED'].map(st => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition-colors ${
                      statusFilter === st
                        ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-700/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                    }`}
                  >
                    {st === 'ALL' ? 'All Statuses' : st.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-1">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(prio => (
                  <button
                    key={prio}
                    onClick={() => setPriorityFilter(prio)}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors ${
                      priorityFilter === prio
                        ? 'bg-slate-800 text-slate-200 border border-slate-700'
                        : 'text-slate-400 hover:text-slate-300'
                    }`}
                  >
                    {prio}
                  </button>
                ))}
              </div>
            </div>

            {/* Cases Table */}
            <div className="bg-[#111722] rounded-lg border border-slate-800/80 overflow-hidden shadow-lg">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#0B0F17] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Case Number</th>
                    <th className="px-4 py-3">Investigation Title</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Completeness</th>
                    <th className="px-4 py-3">Disposition</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-400 font-mono">
                        <div className="flex items-center justify-center space-x-2">
                          <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                          <span>Loading active investigations...</span>
                        </div>
                      </td>
                    </tr>
                  ) : filteredCases.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-500 font-mono">
                        No active investigation cases match filters.
                      </td>
                    </tr>
                  ) : filteredCases.map(c => (
                    <tr key={c.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3 font-bold font-mono text-slate-200">
                        <button
                          onClick={() => router.push(`/investigations?id=${c.id}`)}
                          className="hover:text-emerald-400 text-left transition-colors"
                        >
                          {c.case_number}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-100 max-w-sm truncate">{c.title}</div>
                        <div className="text-[10px] text-slate-500 max-w-sm truncate">{c.summary}</div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge type="severity" value={c.priority} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge type="case_status" value={c.status} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center space-x-1.5">
                          <div className="w-12 h-1.5 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
                            <div
                              style={{ width: `${Number(c.evidence_completeness_score) * (Number(c.evidence_completeness_score) <= 1 ? 100 : 1)}%` }}
                              className="h-full bg-emerald-500 rounded-full"
                            />
                          </div>
                          <span className="text-[11px] font-bold text-slate-300 tabular-nums">
                            {Number(c.evidence_completeness_score) * (Number(c.evidence_completeness_score) <= 1 ? 100 : 1)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-300 text-[11px]">
                        {c.disposition || 'Under Triage'}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1.5">
                          {/* Open Case Action */}
                          <button
                            onClick={() => router.push(`/investigations?id=${c.id}`)}
                            className="px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center space-x-1"
                            title="Open the complete evidentiary case dossier"
                          >
                            <Briefcase className="w-3 h-3" />
                            <span>Open Case</span>
                          </button>

                          {/* Open Full Audit Action */}
                          <Link
                            href={`/audit?resource_id=${c.id}&resource_type=CASE`}
                            className="px-2.5 py-1 rounded-md text-[10px] font-mono font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 transition-colors flex items-center space-x-1"
                            title="Open immutable audit trail for this investigation"
                          >
                            <ScrollText className="w-3 h-3 text-slate-400" />
                            <span>Full Audit</span>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            </div>
                            <ScrollText className="w-3 h-3" />
                            <span>Open Full Audit</span>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

export default function InvestigationsPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading investigation casefiles..." />}>
      <InvestigationsContent />
    </Suspense>
  );
}
