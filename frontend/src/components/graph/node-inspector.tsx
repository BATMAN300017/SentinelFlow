'use client';

import React from 'react';
import { GraphNode } from '@/types/entity';
import { StatusBadge } from '@/components/shared/status-badge';
import { ShieldAlert, ExternalLink, X } from 'lucide-react';
import Link from 'next/link';

interface NodeInspectorProps {
  node: GraphNode | null;
  onClose?: () => void;
}

export function NodeInspector({ node, onClose }: NodeInspectorProps) {
  if (!node) {
    return (
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 text-center py-12 text-xs font-mono text-slate-500">
        Select a node in the graph constellation to inspect entity properties and structural centrality.
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold text-sky-400">{node.id}</span>
            <StatusBadge type="severity" value={node.risk_level} />
          </div>
          <h4 className="text-sm font-semibold text-slate-100 font-mono">{node.label}</h4>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="space-y-3 text-xs font-mono">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-850">
            <span className="text-slate-500 text-[10px]">Entity Classification</span>
            <div className="font-bold text-slate-200 mt-0.5">{node.type}</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-850">
            <span className="text-slate-500 text-[10px]">Ledger Balance</span>
            <div className="font-bold text-emerald-400 mt-0.5">
              INR {(node.properties?.balance || 145000).toLocaleString()}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Graph Topology Metrics
          </div>
          <div className="flex justify-between text-slate-400 text-xs">
            <span>In-Degree / Fan-In:</span>
            <span className="text-slate-200 font-bold">14 edges</span>
          </div>
          <div className="flex justify-between text-slate-400 text-xs">
            <span>Out-Degree / Fan-Out:</span>
            <span className="text-slate-200 font-bold">3 edges</span>
          </div>
          <div className="flex justify-between text-slate-400 text-xs">
            <span>Betweenness Centrality:</span>
            <span className="text-sky-400 font-bold">0.784</span>
          </div>
        </div>
      </div>

      <div className="pt-2 flex justify-end">
        <Link
          href={`/entities/${node.id}`}
          className="flex items-center space-x-1.5 text-xs font-mono font-bold text-sky-400 hover:text-sky-300"
        >
          <span>Open Full Account Profile</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
