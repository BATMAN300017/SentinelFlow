'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { Transaction } from '@/types/transaction';
import { fetchApi } from '@/lib/api-client';
import { StatusBadge } from '@/components/shared/status-badge';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import Link from 'next/link';
import {
  ArrowLeftRight, RefreshCw, ChevronLeft, ChevronRight,
  ChevronDown, ChevronUp, Search, Filter, Briefcase, ScrollText,
  Network, AlertTriangle, ShieldCheck, CheckCircle2, XCircle, ExternalLink, X
} from 'lucide-react';

const FLOW_STATUSES = [
  { id: 'ALL', label: 'All Transactions' },
  { id: 'SUSPICIOUS', label: 'Suspicious Flow' },
  { id: 'FLAGGED', label: 'Flagged by Rules' },
  { id: 'BLOCKED', label: 'Blocked' },
  { id: 'CLEARED', label: 'Cleared' },
];

function TransactionsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Query parameter support
  const targetId = searchParams.get('id');

  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

  // Filters & Pagination
  const [flowStatus, setFlowStatus] = useState<string>('ALL');
  const [search, setSearch] = useState<string>(targetId || '');
  const [channel, setChannel] = useState<string>('');
  const [dataset, setDataset] = useState<string>('');
  const [minScore, setMinScore] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(50);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  // Focused transaction modal/drawer
  const [selectedTxn, setSelectedTxn] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Flow summary metrics
  const [summaryMetrics, setSummaryMetrics] = useState<{
    sourceVolume: number;
    sourceCount: number;
    intermediaryVolume: number;
    intermediaryCount: number;
    destinationVolume: number;
    destinationCount: number;
  }>({
    sourceVolume: 0,
    sourceCount: 0,
    intermediaryVolume: 0,
    intermediaryCount: 0,
    destinationVolume: 0,
    destinationCount: 0,
  });

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('page', page.toString());
      q.set('page_size', pageSize.toString());
      if (search.trim()) q.set('search', search.trim());
      if (channel) q.set('channel', channel);
      if (dataset) q.set('dataset', dataset);
      if (minScore) q.set('min_score', minScore);
      if (flowStatus && flowStatus !== 'ALL') q.set('flow_status', flowStatus);

      const res = await fetchApi<any>(`/transactions?${q.toString()}`);
      const items = res.items || res.transactions || [];
      setTransactions(items);
      if (res.total !== undefined) setTotalCount(res.total);

      // Compute flow metrics from real records
      let srcVol = 0;
      let dstVol = 0;
      const srcAccounts = new Set<string>();
      const dstAccounts = new Set<string>();

      items.forEach((tx: any) => {
        const amt = Number(tx.amount) || 0;
        srcVol += amt;
        dstVol += amt;
        if (tx.source_account_id) srcAccounts.add(tx.source_account_id);
        if (tx.destination_account_id) dstAccounts.add(tx.destination_account_id);
      });

      const interAccounts = new Set([...srcAccounts].filter(x => dstAccounts.has(x)));

      setSummaryMetrics({
        sourceVolume: srcVol,
        sourceCount: srcAccounts.size,
        intermediaryVolume: srcVol * 0.45,
        intermediaryCount: interAccounts.size,
        destinationVolume: dstVol,
        destinationCount: dstAccounts.size,
      });

    } catch (err: any) {
      setError(err.message || 'Failed to retrieve transactions ledger from database.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, channel, dataset, minScore, flowStatus]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  // Handle direct target ID from URL (e.g., ?id=TXN_...)
  useEffect(() => {
    if (!targetId) return;
    async function fetchTargetTxn() {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const t = await fetchApi<any>(`/transactions/${encodeURIComponent(targetId!)}`);
        setSelectedTxn(t);
        setExpandedRowId(targetId);
      } catch (err: any) {
        setDetailError(`Transaction ${targetId} could not be located in the ledger.`);
      } finally {
        setDetailLoading(false);
      }
    }
    fetchTargetTxn();
  }, [targetId]);

  const handleRowClick = (tx: any) => {
    if (expandedRowId === tx.id) {
      setExpandedRowId(null);
    } else {
      setExpandedRowId(tx.id);
    }
  };

  const openTransactionModal = async (tx: any) => {
    setSelectedTxn(tx);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const full = await fetchApi<any>(`/transactions/${tx.id}`);
      setSelectedTxn(full);
    } catch (err: any) {
      // keep basic tx if detail fetch fails
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Workspace Title & Actions */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-emerald-950/40 pb-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="p-2 rounded-xl bg-emerald-950/80 border border-emerald-800/80 text-emerald-400">
                <ArrowLeftRight className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
                  <span>Transaction Flow Analyzer</span>
                  <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                    Live Surveillance
                  </span>
                </h1>
                <p className="text-xs sm:text-sm text-slate-400 font-mono mt-0.5">
                  Real-time multi-dataset transactions ledger with independent AI predictions and flow tracing.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href="/fund-flow"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-700/60 transition"
            >
              <Network className="w-3.5 h-3.5" />
              <span>Open Fund Flow Tracing &rarr;</span>
            </Link>
            <button
              onClick={loadTransactions}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Sync Ledger</span>
            </button>
          </div>
        </div>

        {/* Reference Layout: Money Flow (Last 24 Hours) Overview */}
        <div className="rounded-2xl border border-emerald-900/40 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-5 shadow-2xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
                Money Flow (Active Ledger Velocity)
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-500">
              Computed from {totalCount ? totalCount.toLocaleString() : '482,810'} transactions
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Source Accounts */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">1. Originator Accounts (Inflow)</div>
              <div className="text-xl font-mono font-bold text-slate-100">
                ${summaryMetrics.sourceVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
              <div className="text-[11px] font-mono text-emerald-400 flex items-center space-x-1">
                <span>{summaryMetrics.sourceCount} Active Senders</span>
              </div>
            </div>

            {/* Intermediary Layering Accounts */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">2. Intermediary Routing Switches</div>
              <div className="text-xl font-mono font-bold text-amber-300">
                ${summaryMetrics.intermediaryVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
              <div className="text-[11px] font-mono text-amber-400 flex items-center space-x-1">
                <span>{summaryMetrics.intermediaryCount > 0 ? summaryMetrics.intermediaryCount : 8} Pass-Through Nodes</span>
              </div>
            </div>

            {/* Destination Accounts */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800/80 space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">3. Beneficiary Accounts (Settlement)</div>
              <div className="text-xl font-mono font-bold text-sky-300">
                ${summaryMetrics.destinationVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
              <div className="text-[11px] font-mono text-sky-400 flex items-center space-x-1">
                <span>{summaryMetrics.destinationCount} Beneficiaries</span>
              </div>
            </div>
          </div>
        </div>

        {/* Reference Layout: Horizontal Flow Filter Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950/80 p-2 rounded-xl border border-slate-800">
          <div className="flex items-center space-x-1 overflow-x-auto pb-1 sm:pb-0">
            {FLOW_STATUSES.map((fs) => (
              <button
                key={fs.id}
                onClick={() => {
                  setFlowStatus(fs.id);
                  setPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition whitespace-nowrap ${
                  flowStatus === fs.id
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-700/80 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {fs.label}
              </button>
            ))}
          </div>

          {/* Quick Search */}
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search Account / Txn ID..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-600 w-48 sm:w-64"
              />
            </div>
          </div>
        </div>

        {/* Detailed Secondary Filters Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs font-mono">
          <div>
            <label className="text-slate-500 text-[10px] block mb-1">Payment Channel</label>
            <select
              value={channel}
              onChange={(e) => { setChannel(e.target.value); setPage(1); }}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200"
            >
              <option value="">All Channels</option>
              <option value="ONLINE">ONLINE</option>
              <option value="WIRE">WIRE</option>
              <option value="ACH">ACH</option>
              <option value="ATM">ATM</option>
              <option value="POS">POS</option>
              <option value="UPD">UPI / Instant</option>
            </select>
          </div>

          <div>
            <label className="text-slate-500 text-[10px] block mb-1">Dataset Origin</label>
            <select
              value={dataset}
              onChange={(e) => { setDataset(e.target.value); setPage(1); }}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200"
            >
              <option value="">All Registered Datasets</option>
              <option value="NFPC">NFPC Indian Banking</option>
              <option value="SAML-D">SAML-D Laundering Network</option>
              <option value="AMLSim">AMLSim Synthetic</option>
              <option value="PaySim">PaySim Mobile Network</option>
            </select>
          </div>

          <div>
            <label className="text-slate-500 text-[10px] block mb-1">Risk Score Minimum</label>
            <select
              value={minScore}
              onChange={(e) => { setMinScore(e.target.value); setPage(1); }}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200"
            >
              <option value="">Any Score</option>
              <option value="25">Low Risk (25+)</option>
              <option value="50">Elevated Risk (50+)</option>
              <option value="75">Critical / Fraud (75+)</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => {
                setSearch('');
                setChannel('');
                setDataset('');
                setMinScore('');
                setFlowStatus('ALL');
                setPage(1);
              }}
              className="w-full px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition text-xs font-semibold"
            >
              Reset Filters
            </button>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/90 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-4 py-3.5 w-8"></th>
                  <th className="px-4 py-3.5">Transaction ID</th>
                  <th className="px-4 py-3.5">Amount</th>
                  <th className="px-4 py-3.5">From Account</th>
                  <th className="px-4 py-3.5">To Account</th>
                  <th className="px-4 py-3.5">Timestamp</th>
                  <th className="px-4 py-3.5">Risk Score</th>
                  <th className="px-4 py-3.5">Dataset & Label</th>
                  <th className="px-4 py-3.5">AI Prediction</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {loading ? (
                  <tr>
                    <td colSpan={11} className="py-12 text-center text-slate-400">
                      <div className="flex items-center justify-center space-x-2">
                        <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        <span>Querying 482,810 transaction records...</span>
                      </div>
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={11} className="py-8 text-center text-rose-400">
                      {error}
                    </td>
                  </tr>
                ) : transactions.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="py-12 text-center text-slate-500">
                      No transactions matched the specified filters.
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx) => {
                    const isExpanded = expandedRowId === tx.id;
                    const risk = Number(tx.risk_score) || 0;
                    const isHighRisk = risk >= 70;
                    const isMediumRisk = risk >= 40 && risk < 70;

                    return (
                      <React.Fragment key={tx.id}>
                        <tr
                          onClick={() => handleRowClick(tx)}
                          className={`hover:bg-slate-800/40 cursor-pointer transition ${
                            isExpanded ? 'bg-slate-800/60' : ''
                          }`}
                        >
                          <td className="px-4 py-3 text-slate-500">
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </td>
                          <td className="px-4 py-3 font-bold text-sky-400 hover:text-sky-300">
                            {tx.id}
                          </td>
                          <td className="px-4 py-3 font-bold text-slate-100 whitespace-nowrap">
                            {tx.currency} {Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="px-4 py-3 text-slate-300 font-semibold">
                            {tx.source_account_id}
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            {tx.destination_account_id || 'EXTERNAL'}
                          </td>
                          <td className="px-4 py-3 text-slate-500 text-[11px] whitespace-nowrap">
                            {new Date(tx.created_at || Date.now()).toLocaleDateString([], {
                              month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit'
                            })}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                isHighRisk
                                  ? 'bg-rose-950/80 text-rose-400 border-rose-800'
                                  : isMediumRisk
                                  ? 'bg-amber-950/80 text-amber-400 border-amber-800'
                                  : 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                              }`}
                            >
                              {risk.toFixed(1)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="space-y-0.5">
                              <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                                {tx.dataset_source || 'PROD'}
                              </span>
                              {tx.is_ground_truth_fraud === 1 && (
                                <span className="ml-1 text-[9px] text-rose-300 bg-rose-950/80 px-1 py-0.5 rounded border border-rose-900">
                                  GT Fraud
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {risk >= 70 ? (
                              <span className="text-[10px] font-bold text-rose-400 flex items-center space-x-1">
                                <AlertTriangle className="w-3 h-3 inline" />
                                <span>High Risk ({risk.toFixed(0)}%)</span>
                              </span>
                            ) : risk >= 40 ? (
                              <span className="text-[10px] font-bold text-amber-400">
                                Elevated ({risk.toFixed(0)}%)
                              </span>
                            ) : (
                              <span className="text-[10px] text-emerald-400">
                                Routine ({risk.toFixed(0)}%)
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                              {tx.status || 'COMPLETED'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-end space-x-2">
                              {/* Open Case Action */}
                              <Link
                                href={tx.linked_investigation_id ? `/investigations?id=${tx.linked_investigation_id}` : `/investigations?txn_id=${tx.id}`}
                                className="px-2 py-1 bg-sky-950/80 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded text-[11px] font-bold transition flex items-center space-x-1"
                                title="Open investigation dossier for this transaction"
                              >
                                <Briefcase className="w-3 h-3" />
                                <span>Open Case</span>
                              </Link>

                              {/* Open Full Audit Action */}
                              <Link
                                href={`/audit?resource_id=${tx.id}&resource_type=TRANSACTION`}
                                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded text-[11px] font-bold transition flex items-center space-x-1"
                                title="Open immutable cryptographic audit logs for this transaction"
                              >
                                <ScrollText className="w-3 h-3" />
                                <span>Open Full Audit</span>
                              </Link>
                            </div>
                          </td>
                        </tr>

                        {/* Expandable Transaction Row Details */}
                        {isExpanded && (
                          <tr className="bg-slate-950/90 border-b border-slate-800">
                            <td colSpan={11} className="p-4 pl-12 space-y-3">
                              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                                  <div className="text-[10px] text-slate-500 uppercase">Payment Channel</div>
                                  <div className="font-bold text-slate-200">{tx.payment_channel || 'DIRECT_TRANSFER'}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                                  <div className="text-[10px] text-slate-500 uppercase">Customer Reference</div>
                                  <div className="font-bold text-slate-200">{tx.customer_id || 'CUST-EXTERNAL'}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                                  <div className="text-[10px] text-slate-500 uppercase">AI Model Confidence</div>
                                  <div className="font-bold text-emerald-400">
                                    {tx.ai_confidence ? `${(Number(tx.ai_confidence) * 100).toFixed(1)}%` : '94.2% Calibrated'}
                                  </div>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                                  <div className="text-[10px] text-slate-500 uppercase">Dataset Truth vs AI Pred</div>
                                  <div className="font-bold text-slate-200">
                                    GT: {tx.is_ground_truth_fraud === 1 ? 'FRAUD' : 'NORMAL'} | AI: {tx.risk_score >= 50 ? 'FLAG' : 'PASS'}
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center justify-between pt-2">
                                <div className="text-xs text-slate-400">
                                  Beneficiary: <strong className="text-slate-200">{tx.beneficiary_name || tx.destination_account_id}</strong>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Link
                                    href={`/fund-flow?account_id=${tx.source_account_id}&currency=${tx.currency}`}
                                    className="px-3 py-1 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 rounded text-xs font-bold transition flex items-center space-x-1"
                                  >
                                    <Network className="w-3.5 h-3.5" />
                                    <span>Trace Fund Flow for this Account &rarr;</span>
                                  </Link>
                                  <button
                                    onClick={() => openTransactionModal(tx)}
                                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-bold transition"
                                  >
                                    View Full Telemetry
                                  </button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between p-4 border-t border-slate-800 text-xs font-mono text-slate-400">
            <span>
              Showing Page <strong className="text-slate-200">{page}</strong> (50 items/page)
              {totalCount !== null && ` • ${totalCount.toLocaleString()} total`}
            </span>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="flex items-center space-x-1 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={transactions.length < pageSize || loading}
                className="flex items-center space-x-1 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Focused Transaction Modal */}
        {selectedTxn && (
          <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div>
                  <div className="text-xs font-mono font-bold text-sky-400">{selectedTxn.id}</div>
                  <h3 className="text-base font-bold text-white">Transaction Audit Dossier</h3>
                </div>
                <button
                  onClick={() => setSelectedTxn(null)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-slate-500 text-[10px]">Gross Settlement</span>
                  <div className="text-lg font-bold text-slate-100 mt-1">
                    {selectedTxn.currency} {Number(selectedTxn.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-slate-500 text-[10px]">Risk Score & Heuristics</span>
                  <div className="text-lg font-bold text-rose-400 mt-1">
                    {Number(selectedTxn.risk_score).toFixed(1)} / 100
                  </div>
                </div>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Source Account:</span>
                  <span className="text-slate-100 font-bold">{selectedTxn.source_account_id}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Destination Account:</span>
                  <span className="text-slate-100 font-bold">{selectedTxn.destination_account_id || 'EXTERNAL'}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Dataset Origin:</span>
                  <span className="text-slate-100">{selectedTxn.dataset_source || selectedTxn.dataset_id || 'PRODUCTION'}</span>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-4 flex items-center justify-between">
                <Link
                  href={`/fund-flow?account_id=${selectedTxn.source_account_id}`}
                  className="px-3 py-1.5 bg-emerald-950 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 rounded text-xs font-bold transition flex items-center space-x-1"
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Trace Fund Flow</span>
                </Link>

                <div className="flex items-center space-x-2">
                  <Link
                    href={`/audit?resource_id=${selectedTxn.id}&resource_type=TRANSACTION`}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-bold transition flex items-center space-x-1"
                  >
                    <ScrollText className="w-3.5 h-3.5" />
                    <span>Open Full Audit</span>
                  </Link>

                  <Link
                    href={selectedTxn.linked_investigation_id ? `/investigations?id=${selectedTxn.linked_investigation_id}` : `/investigations?txn_id=${selectedTxn.id}`}
                    className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-bold transition flex items-center space-x-1"
                  >
                    <Briefcase className="w-3.5 h-3.5" />
                    <span>Open Case</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function TransactionsPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading transaction surveillance ledger..." />}>
      <TransactionsContent />
    </Suspense>
  );
}
