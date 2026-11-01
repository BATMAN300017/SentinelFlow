'use client';

import React, { useState } from 'react';
import { GraphData, GraphNode, GraphEdge } from '@/types/entity';

interface RelationshipGraphProps {
  graphData?: GraphData;
  onSelectNode?: (node: GraphNode) => void;
  selectedNodeId?: string | null;
}

export function RelationshipGraph({
  graphData,
  onSelectNode,
  selectedNodeId,
}: RelationshipGraphProps) {
  const [zoom, setZoom] = useState(1);

  const defaultNodes: GraphNode[] = [
    { id: 'ACCT_000038', label: 'Originator 038', type: 'ACCOUNT', risk_level: 'ROUTINE', properties: { balance: 1420000, flagged: false } },
    { id: 'ACCT_000104', label: 'Mule Layer 104', type: 'ACCOUNT', risk_level: 'HIGH', properties: { balance: 45000, flagged: true, is_mule: true } },
    { id: 'ACCT_000219', label: 'Mule Layer 219', type: 'ACCOUNT', risk_level: 'ELEVATED', properties: { balance: 12000, flagged: true, is_mule: true } },
    { id: 'ACCT_000892', label: 'Sink Account 892', type: 'ACCOUNT', risk_level: 'CRITICAL', properties: { balance: 890000, flagged: true } },
    { id: 'ACCT_000551', label: 'Legitimate Branch', type: 'ACCOUNT', risk_level: 'LOW', properties: { balance: 350000, flagged: false } },
  ];

  const defaultEdges: GraphEdge[] = [
    { source: 'ACCT_000038', target: 'ACCT_000104', amount: 500000, currency: 'INR', label: 'RTGS Transfer' },
    { source: 'ACCT_000104', target: 'ACCT_000219', amount: 245000, currency: 'INR', label: 'IMPS Sweep' },
    { source: 'ACCT_000104', target: 'ACCT_000892', amount: 240000, currency: 'INR', label: 'Immediate Forward' },
    { source: 'ACCT_000219', target: 'ACCT_000892', amount: 235000, currency: 'INR', label: 'Syndicate Consolidate' },
    { source: 'ACCT_000038', target: 'ACCT_000551', amount: 45000, currency: 'INR', label: 'Vendor Payout' },
  ];

  const nodes = graphData?.nodes && graphData.nodes.length > 0 ? graphData.nodes : defaultNodes;
  const edges = graphData?.edges && graphData.edges.length > 0 ? graphData.edges : defaultEdges;

  // Compute fixed 2D positions in a circular/star constellation
  const width = 700;
  const height = 420;
  const centerX = width / 2;
  const centerY = height / 2;

  const positions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n, idx) => {
    if (idx === 0) {
      positions[n.id] = { x: 120, y: centerY };
    } else if (idx === nodes.length - 1) {
      positions[n.id] = { x: width - 120, y: centerY };
    } else {
      const angle = ((idx - 1) / (nodes.length - 2)) * Math.PI - Math.PI / 2;
      const radius = 170;
      positions[n.id] = {
        x: centerX + Math.cos(angle) * (radius * 0.9),
        y: centerY + Math.sin(angle) * radius,
      };
    }
  });

  const getNodeColor = (node: GraphNode) => {
    switch (node.risk_level) {
      case 'CRITICAL':
      case 'HIGH':
        return '#f43f5e'; // rose-500
      case 'ELEVATED':
        return '#f59e0b'; // amber-500
      case 'LOW':
        return '#0284c7'; // sky-600
      default:
        return '#10b981'; // emerald-500
    }
  };

  return (
    <div className="relative w-full h-[450px] rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl flex items-center justify-center">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-40 pointer-events-none" />

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="22"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#38bdf8" />
          </marker>
        </defs>

        {/* Directed Edges */}
        {edges.map((e, idx) => {
          const src = positions[e.source] || { x: 150, y: 150 };
          const tgt = positions[e.target] || { x: 350, y: 350 };
          const midX = (src.x + tgt.x) / 2;
          const midY = (src.y + tgt.y) / 2;

          return (
            <g key={idx} className="group">
              <line
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke="#334155"
                strokeWidth="1.5"
                strokeDasharray="4 2"
                markerEnd="url(#arrowhead)"
                className="group-hover:stroke-sky-400 group-hover:stroke-2 transition"
              />
              <text
                x={midX}
                y={midY - 6}
                fill="#94a3b8"
                fontSize="9"
                fontFamily="monospace"
                textAnchor="middle"
                className="opacity-60 group-hover:opacity-100 transition"
              >
                {e.currency} {Number(e.amount).toLocaleString()}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((n) => {
          const pos = positions[n.id] || { x: centerX, y: centerY };
          const isSelected = selectedNodeId === n.id;
          const color = getNodeColor(n);

          return (
            <g
              key={n.id}
              onClick={() => onSelectNode && onSelectNode(n)}
              className="cursor-pointer group"
              transform={`translate(${pos.x}, ${pos.y})`}
            >
              {isSelected && (
                <circle r="22" fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="3 3" className="animate-spin" />
              )}
              <circle
                r="14"
                fill="#0f172a"
                stroke={color}
                strokeWidth="2.5"
                className="group-hover:scale-125 transition-transform duration-200"
              />
              <circle r="4" fill={color} />
              <text
                y="26"
                fill="#e2e8f0"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="600"
                textAnchor="middle"
                className="group-hover:fill-sky-400 transition"
              >
                {n.label || n.id}
              </text>
              <text
                y="37"
                fill="#64748b"
                fontSize="8"
                fontFamily="monospace"
                textAnchor="middle"
              >
                {n.risk_level}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
