'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { fetchApi } from '@/lib/api-client';
import { AppShell } from '@/components/layout/app-shell';
import Link from 'next/link';
import {
  ShieldAlert, RefreshCw, Briefcase, ScrollText, Network,
  ExternalLink, AlertTriangle, ArrowLeftRight, CheckCircle2, ChevronRight, X
} from 'lucide-react';
import { LoadingState } from '@/components/shared/loading-state';

function AlertsContent() {
  const searchParams = useSearchParams();
  const targetAlertId = searchParams.get('id');

  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [investigatingId, setInvestigatingId] = useState<string | null>(null);
  const [selectedDossier, setSelectedDossier] = useState<any | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');

  useEffect(() => {
    loadAlerts();
  }, []);

  // Handle direct navigation to a specific alert via query param ?id=...
  useEffect(() => {
    if (!targetAlertId) return;
    handleInvestigate(targetAlertId);
  }, [targetAlertId]);

  async function loadAlerts() {
    setLoading(true);
    try {
      const res = await fetchApi<any>('/alerts?page_size=50');
      setAlerts(res.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleInvestigate(alertId: string) {
    setInvestigatingId(alertId);
    try {
      const res = await fetchApi<any>(`/alerts/${alertId}/investigate`, { method: 'POST' });
      if (res.scam_dossier) {
        setSelectedDossier(res.scam_dossier);
        setModalOpen(true);
        loadAlerts();
      }
    } catch (e: any) {
      alert("Failed to investigate alert: " + (e.message || e));
    } finally {
      setInvestigatingId(null);
    }
  }

  const filteredAlerts = alerts.filter(a => {
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
    if (search.trim()) {
      const s = search.toLowerCase();
      const matchRef = a.alert_ref?.toLowerCase().includes(s);
      const matchAcc = a.account_id?.toLowerCase().includes(s);
      const matchTxn = a.transaction_id?.toLowerCase().includes(s);
      if (!matchRef && !matchAcc && !matchTxn) return false;
    }
    return true;
  });

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-rose-950/40 pb-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="p-2 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-400">
                <ShieldAlert className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
                  <span>Alerts Queue & Triage</span>
                  <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800">
                    High Priority Heuristics
                  </span>
                </h1>
                <p className="text-xs sm:text-sm text-slate-400 font-mono mt-0.5">
                  Review incoming financial crime alerts produced by multi-signal fraud heuristics and graph topology.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href="/investigations"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-sky-950/60 hover:bg-sky-900/80 text-sky-300 border border-sky-700/60 transition"
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Go to Investigations &rarr;</span>
            </Link>
            <button
              onClick={loadAlerts}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Alerts</span>
            </button>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950/80 p-3 rounded-xl border border-slate-800">
          <div className="flex items-center space-x-1">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(sev => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition ${
                  severityFilter === sev
                    ? 'bg-rose-950 text-rose-400 border border-rose-700/80 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {sev === 'ALL' ? 'All Severities' : sev}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Filter Alert, Account, or Txn ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-rose-600 w-48 sm:w-64"
            />
          </div>
        </div>

        {/* Alerts Table */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl backdrop-blur-sm">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/90 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Alert Ref</th>
                <th className="px-5 py-3.5">Severity</th>
                <th className="px-5 py-3.5">Risk Score</th>
                <th className="px-5 py-3.5">Account ID</th>
                <th className="px-5 py-3.5">Linked Transaction</th>
                <th className="px-5 py-3.5">Typology & Findings</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400 font-mono">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
                      <span>Loading active alerts queue...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500 font-mono">
                    No active alerts matching criteria.
                  </td>
                </tr>
              ) : filteredAlerts.map(a => (
                <tr key={a.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-5 py-3.5 font-mono font-bold text-sky-400">
                    {a.alert_ref}
                  </td>
                  <td className="px-5 py-3.5 font-semibold">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${
                      a.severity === 'CRITICAL' ? 'bg-rose-950/80 text-rose-400 border-rose-800' :
                      a.severity === 'HIGH' ? 'bg-amber-950/80 text-amber-400 border-amber-800' :
                      'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      {a.severity}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-100">
                    {Number(a.risk_score).toFixed(1)}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-slate-300">
                    <Link
                      href={`/fund-flow?account_id=${a.account_id}`}
                      className="text-sky-400 hover:text-sky-300 underline underline-offset-2"
                      title="Trace fund flow for this account"
                    >
                      {a.account_id}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-slate-400">
                    {a.transaction_id ? (
                      <Link
                        href={`/transactions?id=${a.transaction_id}`}
                        className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2"
                      >
                        {a.transaction_id}
                      </Link>
                    ) : (
                      <span className="text-slate-600">AGGREGATED_STREAM</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-slate-300 font-mono max-w-xs truncate" title={a.summary || a.title}>
                    {a.title}
                  </td>
                  <td className="px-5 py-3.5 text-slate-400 font-mono text-xs">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                      {a.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end space-x-2">
                      {/* Open Case Action */}
                      <button
                        onClick={() => handleInvestigate(a.id)}
                        disabled={investigatingId === a.id}
                        className="bg-sky-600 hover:bg-sky-500 text-white font-mono text-[11px] px-2.5 py-1.5 rounded-lg font-bold shadow-sm transition flex items-center space-x-1 disabled:opacity-50"
                        title="Open or convert this alert into an investigation case dossier"
                      >
                        <Briefcase className="w-3 h-3" />
                        <span>{investigatingId === a.id ? 'Loading...' : 'Open Case'}</span>
                      </button>

                      {/* Open Full Audit Action */}
                      <Link
                        href={`/audit?resource_id=${a.id}&resource_type=ALERT`}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono text-[11px] px-2.5 py-1.5 rounded-lg font-bold shadow-sm transition flex items-center space-x-1"
                        title="Open immutable cryptographic audit logs for this alert"
                      >
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

        {/* Scam Dossier & Investigation Route Map Modal */}
        {modalOpen && selectedDossier && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl text-slate-100 max-w-5xl w-full p-6 space-y-5 my-8 max-h-[92vh] overflow-y-auto">
              {/* Modal Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2.5">
                    <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wide">
                      {selectedDossier.scam_category?.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono text-xs text-sky-400 bg-sky-950/80 border border-sky-800 px-2 py-0.5 rounded">
                      {selectedDossier.case_number}
                    </span>
                    <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                      {selectedDossier.status}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-tight">{selectedDossier.scam_title}</h2>
                  <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">{selectedDossier.modus_operandi}</p>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Risk Score</div>
                    <div className="text-2xl font-black text-rose-400 font-mono">
                      {Number(selectedDossier.risk_score).toFixed(1)}
                    </div>
                  </div>
                  <button
                    onClick={() => setModalOpen(false)}
                    className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Geographic & Money-Flow Route Map */}
              <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 text-slate-300 font-medium">
                    <span>Interactive Transaction Movement & Geo-Route Map</span>
                  </div>
                  <div className="flex items-center space-x-3 text-[11px] text-slate-400">
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block"></span>
                      <span>Origin</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 inline-block"></span>
                      <span>Rail Switch</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block"></span>
                      <span>Layering Mule</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
                      <span>Off-Ramp Destination</span>
                    </span>
                  </div>
                </div>

                {/* SVG Canvas Map */}
                <div className="h-72 w-full bg-slate-950 rounded-lg relative overflow-hidden flex items-center justify-center border border-slate-900">
                  <svg viewBox="0 0 850 320" className="w-full h-full">
                    <defs>
                      <linearGradient id="routeGradNext" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#10B981" stopOpacity="0.9"/>
                        <stop offset="35%" stopColor="#6366F1" stopOpacity="0.9"/>
                        <stop offset="70%" stopColor="#F59E0B" stopOpacity="0.9"/>
                        <stop offset="100%" stopColor="#EF4444" stopOpacity="0.9"/>
                      </linearGradient>
                    </defs>
                    <rect width="100%" height="100%" fill="#050814" rx="10"/>
                    <g stroke="#1E293B" strokeWidth="0.75" strokeDasharray="3,3">
                      <line x1="0" y1="80" x2="850" y2="80"/>
                      <line x1="0" y1="160" x2="850" y2="160"/>
                      <line x1="0" y1="240" x2="850" y2="240"/>
                      <line x1="212" y1="0" x2="212" y2="320"/>
                      <line x1="425" y1="0" x2="425" y2="320"/>
                      <line x1="637" y1="0" x2="637" y2="320"/>
                    </g>
                    {/* Draw Bezier and Markers */}
                    {selectedDossier.route_map?.hops?.map((h: any, i: number, arr: any[]) => {
                      const step = 660 / (arr.length - 1 || 1);
                      const x = 95 + i * step;
                      const y = 60 + 200 * (i % 2 === 0 ? 0.35 : 0.65);
                      const nextX = 95 + (i + 1) * step;
                      const nextY = 60 + 200 * ((i + 1) % 2 === 0 ? 0.35 : 0.65);
                      const cx = (x + nextX) / 2;
                      const cy = Math.min(y, nextY) - 38;
                      const color = h.hop_type === 'ORIGIN' ? '#10B981' : h.hop_type === 'TRANSIT_GATEWAY' ? '#6366F1' : h.hop_type === 'INTERMEDIARY_MULE' ? '#F59E0B' : '#EF4444';

                      return (
                        <g key={h.hop_index}>
                          {i < arr.length - 1 && (
                            <>
                              <path d={`M ${x} ${y} Q ${cx} ${cy} ${nextX} ${nextY}`} fill="none" stroke="#334155" strokeWidth="2.5" />
                              <path d={`M ${x} ${y} Q ${cx} ${cy} ${nextX} ${nextY}`} fill="none" stroke="url(#routeGradNext)" strokeWidth="3" strokeDasharray="8,6" />
                            </>
                          )}
                          <circle cx={x} cy={y} r="14" fill={color} fillOpacity="0.25" stroke={color} strokeOpacity="0.5" />
                          <circle cx={x} cy={y} r="8.5" fill="#0B132B" stroke={color} strokeWidth="3.5" />
                          <circle cx={x} cy={y} r="3.5" fill={color} />
                          <rect x={x - 28} y={y - 48} width="56" height="20" rx="4" fill="#0F172A" stroke={color} strokeWidth="1.2" />
                          <text x={x} y={y - 34} fill="#E2E8F0" fontSize="10" fontFamily="monospace" fontWeight="bold" textAnchor="middle">
                            HOP {h.hop_index}
                          </text>
                          <text x={x} y={y + 22} fill="#F8FAFC" fontSize="12" fontWeight="bold" textAnchor="middle">{h.city}</text>
                          <text x={x} y={y + 36} fill="#94A3B8" fontSize="10" textAnchor="middle">{h.country}</text>
                          <text x={x} y={y + 50} fill={color} fontSize="10" fontFamily="monospace" fontWeight="600" textAnchor="middle">
                            {h.amount ? '$' + Number(h.amount).toLocaleString() : ''}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
              </div>

              {/* Hop Cards Trail */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Detailed Hop Trail</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {selectedDossier.route_map?.hops?.map((h: any) => (
                    <div key={h.hop_index} className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-sky-400">HOP {h.hop_index}</span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">{h.hop_type}</span>
                      </div>
                      <div className="font-bold text-slate-200 truncate">{h.title}</div>
                      <div className="text-slate-400 font-semibold">{h.city}, {h.country}</div>
                      <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between font-mono text-[10px]">
                        <span className="text-emerald-400 font-bold">{h.amount ? '$' + Number(h.amount).toLocaleString() : ''}</span>
                        {h.account_id && (
                          <Link
                            href={`/fund-flow?account_id=${h.account_id}`}
                            className="text-sky-400 hover:text-sky-300"
                          >
                            Trace Flow &rarr;
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="border-t border-slate-800 pt-4 flex items-center justify-between">
                <Link
                  href={`/audit?resource_id=${selectedDossier.alert_id || selectedDossier.case_number}&resource_type=ALERT`}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono font-medium transition flex items-center space-x-1"
                >
                  <ScrollText className="w-3.5 h-3.5" />
                  <span>View Case Audit Trail</span>
                </Link>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setModalOpen(false)}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
                  >
                    Close
                  </button>
                  {selectedDossier.investigation_id && (
                    <Link
                      href={`/investigations?id=${selectedDossier.investigation_id}`}
                      className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-medium shadow-sm transition"
                    >
                      Open Full Dossier &rarr;
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function AlertsPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading alert triage queue..." />}>
      <AlertsContent />
    </Suspense>
  );
}
