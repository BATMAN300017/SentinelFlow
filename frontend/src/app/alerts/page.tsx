'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { AppShell } from '@/components/layout/app-shell';
import Link from 'next/link';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [investigatingId, setInvestigatingId] = useState<string | null>(null);
  const [selectedDossier, setSelectedDossier] = useState<any | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    loadAlerts();
  }, []);

  async function loadAlerts() {
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

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">Alerts Queue & Triage</h1>
            <p className="text-slate-400 text-xs font-mono mt-1">Review incoming alerts produced by multi-signal fraud heuristics.</p>
          </div>
          <Link href="/dashboard" className="text-xs font-mono text-sky-400 hover:text-sky-300">&larr; Back to Dashboard</Link>
        </div>

        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 overflow-hidden shadow-xl backdrop-blur-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold font-mono border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3">Alert Ref</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Risk Score</th>
                <th className="px-5 py-3">Account</th>
                <th className="px-5 py-3">Findings</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {loading ? (
                <tr><td colSpan={7} className="text-center py-8 text-slate-400 font-mono">Loading alerts telemetry...</td></tr>
              ) : alerts.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-slate-400 font-mono">No active alerts in review queue</td></tr>
              ) : alerts.map(a => (
                <tr key={a.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-5 py-3 font-mono font-bold text-sky-400">{a.alert_ref}</td>
                  <td className="px-5 py-3 font-semibold">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${
                      a.severity === 'CRITICAL' ? 'bg-rose-950/80 text-rose-400 border-rose-800' :
                      a.severity === 'HIGH' ? 'bg-amber-950/80 text-amber-400 border-amber-800' :
                      'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      {a.severity}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono font-bold text-slate-100">{Number(a.risk_score).toFixed(1)}</td>
                  <td className="px-5 py-3 font-mono text-slate-300">{a.account_id}</td>
                  <td className="px-5 py-3 text-slate-300 font-mono max-w-xs truncate" title={a.summary}>{a.title}</td>
                  <td className="px-5 py-3 text-slate-400 font-mono text-xs">{a.status}</td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => handleInvestigate(a.id)}
                      disabled={investigatingId === a.id}
                      className="bg-sky-600 hover:bg-sky-500 text-white font-mono text-[11px] px-3 py-1.5 rounded-lg font-bold shadow-sm transition flex items-center space-x-1 disabled:opacity-50"
                    >
                      <span>{investigatingId === a.id ? 'Analyzing...' : 'Investigate'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      {/* Scam Dossier & Route Map Modal */}
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
                        <text x={x} y={y + 62} fill="#64748B" fontSize="9" textAnchor="middle">{h.ip_address || ''}</text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Route Summary Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] text-slate-400">
                <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Total Geodesic Span</div>
                  <div className="font-mono text-slate-200 font-semibold mt-0.5">{selectedDossier.route_map?.distance_km} km</div>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Payment Channel</div>
                  <div className="font-mono text-slate-200 font-semibold mt-0.5">{selectedDossier.transaction?.payment_channel}</div>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Exfiltrated Sum</div>
                  <div className="font-mono text-rose-300 font-bold mt-0.5">
                    ${Number(selectedDossier.transaction?.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </div>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Perimeter Status</div>
                  <div className="font-mono text-amber-300 font-semibold mt-0.5">
                    {selectedDossier.route_map?.destination_country !== selectedDossier.route_map?.origin_country ? 'Cross-Border Offshore' : 'Domestic High-Velocity'}
                  </div>
                </div>
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
                    <div className="font-bold text-slate-200 truncate" title={h.entity_name}>{h.title}</div>
                    <div className="text-slate-400 font-semibold">{h.city}, {h.country}</div>
                    <div className="text-slate-500 text-[10px]">{h.notes}</div>
                    <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between font-mono text-[10px]">
                      <span className="text-slate-400">IP: {h.ip_address || 'Switch'}</span>
                      <span className="text-emerald-400 font-bold">{h.amount ? '$' + Number(h.amount).toLocaleString() : ''}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Findings & Exculpatory Analysis */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <span className="text-rose-400">⚠️</span>
                  <span>Multi-Signal Detection Triggers</span>
                </div>
                <div className="space-y-1.5 text-slate-400 text-[11px]">
                  {selectedDossier.findings?.map((f: any) => (
                    <div key={f.id} className="p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-rose-400 font-bold">• [{f.source}] {f.code}:</span> {f.description} (Risk +{f.score_contribution})
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <span className="text-sky-400">⚖️</span>
                  <span>Legitimacy & Exculpatory Factors</span>
                </div>
                <div className="space-y-1.5 text-slate-400 text-[11px]">
                  <ul className="space-y-1">
                    {selectedDossier.exculpatory_analysis?.supports_fraud?.map((s: string, idx: number) => (
                      <li key={idx}><span className="text-rose-400 font-bold">✖ Supports:</span> {s}</li>
                    ))}
                    {selectedDossier.exculpatory_analysis?.contradicts_fraud?.map((c: string, idx: number) => (
                      <li key={idx}><span className="text-emerald-400 font-bold">✔ Contradicts:</span> {c}</li>
                    ))}
                  </ul>
                  {selectedDossier.exculpatory_analysis?.scholarship_or_institution_check && (
                    <div className="p-2 rounded bg-sky-950/60 border border-sky-800 text-sky-200 text-[10px] mt-2">
                      <b>🎓 Institutional / Scholarship Verification:</b> {selectedDossier.exculpatory_analysis.scholarship_or_institution_check.guidance}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="border-t border-slate-800 pt-4 flex items-center justify-between">
              <div className="text-xs text-slate-400">
                Recommended: <span className="text-amber-400 font-medium">{selectedDossier.recommended_actions?.[0]?.action}</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
                >
                  Close
                </button>
                {selectedDossier.investigation_id && (
                  <Link
                    href={`/investigations/${selectedDossier.investigation_id}`}
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
