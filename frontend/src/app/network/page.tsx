'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { RelationshipGraph } from '@/components/graph/relationship-graph';
import { GraphControls } from '@/components/graph/graph-controls';
import { GraphLegend } from '@/components/graph/graph-legend';
import { NodeInspector } from '@/components/graph/node-inspector';
import { SuspiciousPathPanel } from '@/components/graph/suspicious-path-panel';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import { GraphData, GraphNode } from '@/types/entity';
import { RefreshCw } from 'lucide-react';

export default function NetworkPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hopDepth, setHopDepth] = useState(2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<GraphData>(`/graph?max_hops=${hopDepth}`);
      setGraphData(res);
      if (res.nodes && res.nodes.length > 0 && !selectedNode) {
        setSelectedNode(res.nodes[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load network intelligence graph.');
    } finally {
      setLoading(false);
    }
  }, [hopDepth, selectedNode]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    document.title = 'Network Intelligence Graph | SentinelFlow AI';
  }, []);

  return (
    <AppShell>
      <head>
        <title>Network Intelligence Graph | SentinelFlow AI</title>
        <meta name="description" content="Interactive topological transaction graphs, account clustering, and multi-hop mule chain visualization." />
      </head>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
              <span>Network Intelligence</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-slate-800 text-emerald-400 border border-slate-700">
                Topological Surveillance
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
              Interactive fund-flow graphs, fan-in/fan-out hubs, and intermediary mule chains.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <GraphControls
              hopDepth={hopDepth}
              onHopDepthChange={(d) => setHopDepth(d)}
              onResetView={loadGraph}
            />
            <button
              onClick={loadGraph}
              disabled={loading}
              className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <GraphLegend />

        {loading ? (
          <LoadingState message="Computing topological centrality and multi-hop paths..." rows={8} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadGraph} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <RelationshipGraph
                graphData={graphData || undefined}
                selectedNodeId={selectedNode?.id}
                onSelectNode={(node) => setSelectedNode(node)}
              />
              <SuspiciousPathPanel />
            </div>

            <div>
              <NodeInspector node={selectedNode} onClose={() => setSelectedNode(null)} />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
