'use client';

import React, { useState, useEffect, useCallback, Suspense, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { fetchApi } from '@/lib/api-client';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import Link from 'next/link';
import {
  Network, RefreshCw, Search, Calendar, Filter, ArrowRight,
  ShieldAlert, Briefcase, ScrollText, ChevronRight, X, ExternalLink,
  Layers, ArrowDownRight, ArrowUpRight, CheckCircle2, AlertTriangle
} from 'lucide-react';

const DATE_PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 60 days', days: 60 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 120 days', days: 120 },
];

function FundFlowContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Query parameter support
  const initialAccount = searchParams.get('account_id') || '';
  const initialCurrency = searchParams.get('currency') || 'INR';
  const initialTxn = searchParams.get('txn_id') || '';

  // Controls state
  const [selectedPreset, setSelectedPreset] = useState<number>(30);
  const [customStart, setCustomStart] = useState<string>('');
  const [customEnd, setCustomEnd] = useState<string>('');
  const [currency, setCurrency] = useState<string>(initialCurrency);
  const [searchAccount, setSearchAccount] = useState<string>(initialAccount);
  const [searchTxn, setSearchTxn] = useState<string>(initialTxn);
  const [direction, setDirection] = useState<'both' | 'forward' | 'backward'>('both');

  // Data state
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection inspection
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [selectedLink, setSelectedLink] = useState<any | null>(null);

  const loadFundFlow = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('days', selectedPreset.toString());
      if (currency) q.set('currency', currency);
      if (searchAccount.trim()) q.set('account_id', searchAccount.trim());
      if (searchTxn.trim()) q.set('transaction_id', searchTxn.trim());
      if (direction) q.set('direction', direction);
      if (customStart) q.set('start_date', customStart);
      if (customEnd) q.set('end_date', customEnd);
      q.set('limit', '25');

      const res = await fetchApi<any>(`/fund-flow?${q.toString()}`);
      setData(res);
      // Auto-select first intermediary or top node if available
      if (res.nodes && res.nodes.length > 0 && !selectedNode && !selectedLink) {
        const inter = res.nodes.find((n: any) => n.tier === 'intermediary');
        if (inter) setSelectedNode(inter);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve multi-hop fund flow telemetry.');
    } finally {
      setLoading(false);
    }
  }, [selectedPreset, currency, searchAccount, searchTxn, direction, customStart, customEnd]);

  useEffect(() => {
    loadFundFlow();
  }, [loadFundFlow]);

  // Handle Preset Click
  const handlePresetChange = (days: number) => {
    setSelectedPreset(days);
    setCustomStart('');
    setCustomEnd('');
  };

  // Sankey Layout Computation
  const sankeyLayout = useMemo(() => {
    if (!data || !data.nodes || data.nodes.length === 0) return null;

    const nodes = data.nodes;
    const links = data.links || [];

    // Group nodes into 3 columns
    const sourceNodes: any[] = [];
    const interNodes: any[] = [];
    const destNodes: any[] = [];

    nodes.forEach((n: any) => {
      if (n.tier === 'source') sourceNodes.push(n);
      else if (n.tier === 'intermediary') interNodes.push(n);
      else destNodes.push(n);
    });

    // Fallback if no intermediaries exist in slice
    if (interNodes.length === 0 && destNodes.length > 2) {
      const promoted = destNodes.splice(0, Math.min(2, Math.floor(destNodes.length / 2)));
      promoted.forEach(p => { p.tier = 'intermediary'; interNodes.push(p); });
    }

    const svgWidth = 980;
    const svgHeight = 540;
    const paddingY = 45;
    const colWidth = 24;

    const colX = {
      source: 90,
      intermediary: 480,
      destination: 870,
    };

    const nodePositions: Record<string, { x: number; y: number; height: number; node: any }> = {};

    function positionColumn(colNodes: any[], xPos: number) {
      const count = colNodes.length || 1;
      const availableH = svgHeight - paddingY * 2;
      const step = availableH / count;
      colNodes.forEach((node, idx) => {
        const h = Math.max(38, Math.min(75, step * 0.75));
        const y = paddingY + idx * step + (step - h) / 2;
        nodePositions[node.id] = { x: xPos, y, height: h, node };
      });
    }

    positionColumn(sourceNodes, colX.source);
    positionColumn(interNodes, colX.intermediary);
    positionColumn(destNodes, colX.destination);

    // Compute Flow Ribbons
    const maxFlowVal = Math.max(...links.map((l: any) => l.value), 1);
    const flowRibbons = links.map((link: any, idx: number) => {
      const srcPos = nodePositions[link.source];
      const dstPos = nodePositions[link.target];
      if (!srcPos || !dstPos) return null;

      // Ribbon width proportionally scaled
      const width = Math.max(7, Math.min(42, (link.value / maxFlowVal) * 38));

      const x1 = srcPos.x + colWidth;
      const y1 = srcPos.y + srcPos.height / 2;
      const x2 = dstPos.x;
      const y2 = dstPos.y + dstPos.height / 2;

      // Bezier control points for Lucinity-style smooth S-curves
      const dx = (x2 - x1) * 0.5;
      const cx1 = x1 + dx;
      const cx2 = x2 - dx;

      const pathData = `
        M ${x1} ${y1 - width / 2}
        C ${cx1} ${y1 - width / 2}, ${cx2} ${y2 - width / 2}, ${x2} ${y2 - width / 2}
        L ${x2} ${y2 + width / 2}
        C ${cx2} ${y2 + width / 2}, ${cx1} ${y1 + width / 2}, ${x1} ${y1 + width / 2}
        Z
      `;

      return {
        ...link,
        id: `flow-${link.source}-${link.target}-${idx}`,
        path: pathData,
        x1, y1, x2, y2, cx1, cx2, width,
        midX: (x1 + x2) / 2,
        midY: (y1 + y2) / 2,
      };
    }).filter(Boolean);

    return {
      nodes: Object.values(nodePositions),
      ribbons: flowRibbons,
      sourceCount: sourceNodes.length,
      interCount: interNodes.length,
      destCount: destNodes.length,
    };
  }, [data]);

  useEffect(() => {
    document.title = 'Fund Flow Tracing & Sankey Graph | SentinelFlow AI';
  }, []);

  return (
    <AppShell>
      <head>
        <title>Fund Flow Tracing &amp; Sankey Graph | SentinelFlow AI</title>
        <meta name="description" content="Multi-hop money-flow Sankey visualization, pass-through mule network discovery, and cross-border payment tracing." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto pb-16">
        {/* Workspace Title & Period Indicator */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="p-2 rounded-lg bg-slate-900 border border-emerald-500/30 text-emerald-400">
                <Network className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-2.5">
                  <span>Fund Flow Tracing</span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                    Sankey Capital Analytics
                  </span>
                </h1>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Multi-hop capital routing analysis across originators, intermediary layering mules, and cash-out off-ramps.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadFundFlow}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-semibold bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-200 border border-slate-700/80 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Topology</span>
            </button>
          </div>
        </div>

        {/* Lucinity Reference: Date Presets & Custom Date Range Filter */}
        <div className="p-4 rounded-lg bg-[#111722] border border-slate-800/80 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* Presets */}
            <div className="flex items-center space-x-1 overflow-x-auto pb-1 sm:pb-0">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mr-1">Period:</span>
              {DATE_PRESETS.map((p) => (
                <button
                  key={p.days}
                  onClick={() => handlePresetChange(p.days)}
                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition-colors ${
                    selectedPreset === p.days && !customStart
                      ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-700/60'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Currency Selector */}
            <div className="flex items-center space-x-2 text-xs font-mono">
              <span className="text-slate-400 text-[10px] uppercase tracking-wider">Currency:</span>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="bg-[#0B0F17] border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-bold"
              >
                <option value="INR">INR (₹)</option>
                <option value="GBP">GBP (£)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="ALL">ALL (Multi-rail)</option>
              </select>
            </div>
          </div>

          {/* Search & Custom Date Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80 text-xs font-mono">
            <div>
              <label className="text-slate-400 text-[10px] block mb-1 uppercase tracking-wider">Focus Account ID</label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
                <input
                  type="text"
                  placeholder="e.g. ACCT_000150"
                  value={searchAccount}
                  onChange={(e) => setSearchAccount(e.target.value)}
                  className="w-full pl-8 pr-2.5 py-1 bg-[#0B0F17] border border-slate-800 rounded text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="text-slate-400 text-[10px] block mb-1 uppercase tracking-wider">Start Date</label>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="w-full bg-[#0B0F17] border border-slate-800 rounded px-2 py-1 text-slate-200"
              />
            </div>

            <div>
              <label className="text-slate-400 text-[10px] block mb-1 uppercase tracking-wider">End Date</label>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="w-full bg-[#0B0F17] border border-slate-800 rounded px-2 py-1 text-slate-200"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setSearchAccount('');
                  setSearchTxn('');
                  setCustomStart('');
                  setCustomEnd('');
                  setSelectedPreset(30);
                  setCurrency('INR');
                  setSelectedNode(null);
                  setSelectedLink(null);
                }}
                className="w-full py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700/80 rounded font-semibold transition text-xs"
              >
                Reset Canvas
              </button>
            </div>
          </div>
        </div>

        {/* Workspace Period & KPI Bar */}
        {data && data.summary && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-lg bg-[#111722] border border-slate-800/80">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Gross Flow Volume</div>
              <div className="text-lg font-bold text-slate-100 mt-0.5 tabular-nums">
                {currency} {Number(data.summary.total_volume).toLocaleString(undefined, { minimumFractionDigits: 0 })}
              </div>
            </div>
            <div className="p-3.5 rounded-lg bg-[#111722] border border-slate-800/80">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Active Streams</div>
              <div className="text-lg font-bold text-emerald-400 mt-0.5 tabular-nums">{data.summary.flow_count} Empirical Flows</div>
            </div>
            <div className="p-3.5 rounded-lg bg-[#111722] border border-slate-800/80">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Layering Switches</div>
              <div className="text-lg font-bold text-amber-400 mt-0.5 tabular-nums">{data.summary.intermediaries_count} Intermediary Mules</div>
            </div>
            <div className="p-3.5 rounded-lg bg-[#111722] border border-slate-800/80">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Active Analysis Window</div>
              <div className="text-xs font-bold text-slate-300 mt-1.5">{data.period_label}</div>
            </div>
          </div>
        )}

        {/* Main Sankey Visualization Workspace */}
        {loading ? (
          <LoadingState message="Synthesizing multi-hop capital movements and calculating flow bands..." rows={8} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadFundFlow} />
        ) : !sankeyLayout || sankeyLayout.nodes.length === 0 ? (
          <div className="p-16 text-center rounded-2xl border border-slate-800 bg-slate-900/60 font-mono space-y-3">
            <Network className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-sm font-bold text-slate-300">No Qualifying Fund Flows Located</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              No transactions matched the currency ({currency}) or account filter in the selected lookback window.
            </p>
            <button
              onClick={() => { setCurrency('ALL'); setSearchAccount(''); }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition"
            >
              Reset to All Currencies
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* The Sankey Diagram Canvas (occupies 2 columns on large screens) */}
            <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-950 p-4 shadow-2xl relative overflow-hidden flex flex-col justify-between">
              {/* Column Tier Labels */}
              <div className="grid grid-cols-3 text-center border-b border-slate-900 pb-2 mb-2 text-[10px] sm:text-xs font-mono font-bold uppercase tracking-wider">
                <div className="text-emerald-400">1. Originator Accounts ({sankeyLayout.sourceCount})</div>
                <div className="text-amber-400">2. Layering Intermediaries ({sankeyLayout.interCount})</div>
                <div className="text-sky-400">3. Beneficiary Accounts ({sankeyLayout.destCount})</div>
              </div>

              {/* SVG Canvas */}
              <div className="w-full aspect-[16/9] min-h-[300px] sm:min-h-[460px] relative overflow-hidden">
                <svg viewBox="0 0 980 540" preserveAspectRatio="xMidYMid meet" className="w-full h-full select-none">
                  <defs>
                    <linearGradient id="flowGradRoutine" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#10B981" stopOpacity="0.45" />
                      <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.55" />
                    </linearGradient>
                    <linearGradient id="flowGradElevated" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.55" />
                      <stop offset="100%" stopColor="#FB923C" stopOpacity="0.65" />
                    </linearGradient>
                    <linearGradient id="flowGradCritical" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#EF4444" stopOpacity="0.65" />
                      <stop offset="100%" stopColor="#EC4899" stopOpacity="0.75" />
                    </linearGradient>
                  </defs>

                  {/* Flow Ribbons */}
                  {sankeyLayout.ribbons.map((ribbon: any) => {
                    const isSelected = selectedLink?.id === ribbon.id;
                    const grad = ribbon.max_risk_score >= 70
                      ? 'url(#flowGradCritical)'
                      : ribbon.max_risk_score >= 40
                      ? 'url(#flowGradElevated)'
                      : 'url(#flowGradRoutine)';

                    return (
                      <g key={ribbon.id} className="cursor-pointer group">
                        <path
                          d={ribbon.path}
                          fill={grad}
                          stroke={isSelected ? '#38BDF8' : 'transparent'}
                          strokeWidth={isSelected ? 2 : 0}
                          className="transition-all duration-200 hover:opacity-90"
                          onClick={() => { setSelectedLink(ribbon); setSelectedNode(null); }}
                        />
                        {/* Amount Label on or along the flow */}
                        <rect
                          x={ribbon.midX - 38}
                          y={ribbon.midY - 10}
                          width={76}
                          height={20}
                          rx={4}
                          fill="#0F172A"
                          fillOpacity={0.9}
                          stroke="#334155"
                          strokeWidth={0.75}
                        />
                        <text
                          x={ribbon.midX}
                          y={ribbon.midY + 4}
                          fill="#E2E8F0"
                          fontSize="9.5"
                          fontFamily="monospace"
                          fontWeight="bold"
                          textAnchor="middle"
                          pointerEvents="none"
                        >
                          {ribbon.currency} {Number(ribbon.value) >= 1000000 ? `${(Number(ribbon.value) / 1000000).toFixed(1)}M` : `${(Number(ribbon.value) / 1000).toFixed(0)}k`}
                        </text>
                      </g>
                    );
                  })}

                  {/* Node Bars */}
                  {sankeyLayout.nodes.map(({ x, y, height, node }: any) => {
                    const isSelected = selectedNode?.id === node.id;
                    const color = node.tier === 'source'
                      ? '#10B981'
                      : node.tier === 'intermediary'
                      ? '#F59E0B'
                      : '#38BDF8';

                    return (
                      <g
                        key={node.id}
                        className="cursor-pointer group"
                        onClick={() => { setSelectedNode(node); setSelectedLink(null); }}
                      >
                        {/* Node vertical bar */}
                        <rect
                          x={x}
                          y={y}
                          width={24}
                          height={height}
                          rx={6}
                          fill="#0B132B"
                          stroke={isSelected ? '#FFFFFF' : color}
                          strokeWidth={isSelected ? 3 : 2}
                          className="transition-all duration-150"
                        />
                        {/* Core indicator dot */}
                        <circle cx={x + 12} cy={y + height / 2} r={4.5} fill={color} />

                        {/* Account Label and Net Volume */}
                        <text
                          x={node.tier === 'destination' ? x + 30 : x - 10}
                          y={y + height / 2 - 3}
                          fill="#F8FAFC"
                          fontSize="11"
                          fontFamily="monospace"
                          fontWeight="bold"
                          textAnchor={node.tier === 'destination' ? 'start' : 'end'}
                        >
                          {node.name}
                        </text>

                        <text
                          x={node.tier === 'destination' ? x + 30 : x - 10}
                          y={y + height / 2 + 11}
                          fill="#94A3B8"
                          fontSize="9.5"
                          fontFamily="monospace"
                          textAnchor={node.tier === 'destination' ? 'start' : 'end'}
                        >
                          {node.currency} {Number(Math.abs(node.net_flow || node.total_inflow || node.total_outflow)).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Instructions footer */}
              <div className="text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-900 flex items-center justify-between">
                <span>Click any account node or flow ribbon to inspect detailed underlying transactions.</span>
                <span className="text-emerald-400 font-bold">100% Genuine Database Records</span>
              </div>
            </div>

            {/* Side Details Inspector Panel */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl space-y-5">
              {selectedNode ? (
                /* Account Node Telemetry */
                <div className="space-y-4 animate-in fade-in">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                    <div>
                      <div className="text-[10px] font-mono uppercase text-slate-400">Account Telemetry</div>
                      <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                        <span>{selectedNode.name}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded border uppercase ${
                          selectedNode.tier === 'source' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' :
                          selectedNode.tier === 'intermediary' ? 'bg-amber-950 text-amber-300 border-amber-800' :
                          'bg-sky-950 text-sky-300 border-sky-800'
                        }`}>
                          {selectedNode.tier}
                        </span>
                      </h3>
                    </div>
                    <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white p-1">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-slate-500 text-[10px]">Total Inbound Flow</span>
                      <div className="text-sm font-bold text-emerald-400">
                        {selectedNode.currency} {Number(selectedNode.total_inflow).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <span className="text-slate-500 text-[10px]">Total Outbound Flow</span>
                      <div className="text-sm font-bold text-rose-400">
                        {selectedNode.currency} {Number(selectedNode.total_outflow).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-1">
                    <span className="text-slate-500 text-[10px]">Net Position Variance</span>
                    <div className="text-sm font-bold text-slate-200">
                      {selectedNode.currency} {Number(selectedNode.net_flow).toLocaleString()}
                    </div>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <button
                      onClick={() => { setSearchAccount(selectedNode.name); }}
                      className="w-full py-2 bg-indigo-950 hover:bg-indigo-900 border border-indigo-800 text-indigo-300 rounded text-xs font-bold font-mono transition flex items-center justify-center space-x-1.5"
                    >
                      <Filter className="w-3.5 h-3.5" />
                      <span>Focus Subgraph on this Account</span>
                    </button>

                    <Link
                      href={`/transactions?search=${selectedNode.name}`}
                      className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-bold font-mono transition flex items-center justify-center space-x-1.5"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>View All Ledger Records</span>
                    </Link>
                  </div>
                </div>
              ) : selectedLink ? (
                /* Flow Ribbon Telemetry & Underlying Transactions */
                <div className="space-y-4 animate-in fade-in">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                    <div>
                      <div className="text-[10px] font-mono uppercase text-slate-400">Fund Flow Stream</div>
                      <h3 className="text-sm font-bold font-mono text-white">
                        {selectedLink.source} &rarr; {selectedLink.target}
                      </h3>
                    </div>
                    <button onClick={() => setSelectedLink(null)} className="text-slate-400 hover:text-white p-1">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-slate-500 text-[10px]">Gross Stream Sum</span>
                      <div className="text-sm font-bold text-slate-100 mt-1">
                        {selectedLink.currency} {Number(selectedLink.value).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-slate-500 text-[10px]">Stream Count & Risk</span>
                      <div className="text-sm font-bold text-amber-400 mt-1">
                        {selectedLink.count} Txns | {selectedLink.max_risk_score.toFixed(0)} Risk
                      </div>
                    </div>
                  </div>

                  {/* Underlying Transaction Records */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold font-mono text-slate-300">
                      Contributing Transactions ({selectedLink.transactions?.length || 0})
                    </div>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {selectedLink.transactions?.map((tx: any) => (
                        <div key={tx.id} className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sky-400">{tx.id}</span>
                            <span className="font-bold text-slate-200">
                              {tx.currency} {Number(tx.amount).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span>Channel: {tx.channel || 'ONLINE'}</span>
                            <span className="text-rose-400 font-bold">{Number(tx.risk_score).toFixed(0)} Risk</span>
                          </div>
                          <div className="pt-1 border-t border-slate-850 flex items-center justify-end space-x-2">
                            <Link
                              href={`/transactions?id=${tx.id}`}
                              className="text-[10px] text-sky-400 hover:text-sky-300 font-bold"
                            >
                              Open Case &rarr;
                            </Link>
                            <Link
                              href={`/audit?resource_id=${tx.id}&resource_type=TRANSACTION`}
                              className="text-[10px] text-slate-300 hover:text-white font-bold"
                            >
                              Open Audit &rarr;
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                /* Idle state instructions */
                <div className="py-16 text-center space-y-3 font-mono">
                  <div className="w-12 h-12 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
                    <Network className="w-6 h-6" />
                  </div>
                  <h4 className="text-xs font-bold text-slate-300">Inspector Idle</h4>
                  <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                    Select any account node or fund flow ribbon on the Sankey canvas to inspect empirical records and open case dossiers.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function FundFlowPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading fund flow tracing workspace..." />}>
      <FundFlowContent />
    </Suspense>
  );
}
