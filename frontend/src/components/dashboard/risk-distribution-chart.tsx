'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface RiskDistributionProps {
  distribution?: Array<{ bucket: string; count: number }>;
}

const DEFAULT_DATA = [
  { bucket: '0–19', count: 14250, fill: '#687166' },
  { bucket: '20–39', count: 8320, fill: '#B7F34A' },
  { bucket: '40–59', count: 3410, fill: '#FFB800' },
  { bucket: '60–79', count: 1120, fill: '#FF8833' },
  { bucket: '80–100', count: 284, fill: '#FF4D4D' },
];

export function RiskDistributionChart({ distribution }: RiskDistributionProps) {
  const chartData = distribution && distribution.length > 0
    ? distribution.map((d, i) => ({
        ...d,
        fill: [
          '#687166',
          '#B7F34A',
          '#FFB800',
          '#FF8833',
          '#FF4D4D',
        ][i % 5],
      }))
    : DEFAULT_DATA;

  return (
    <div className="p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26]">
      <div className="mb-4">
        <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF]">
          Ensemble Risk Score Density
        </h3>
        <p className="text-[11px] text-[#687166] font-mono mt-0.5">
          Calibrated score distribution across active monitoring window
        </p>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="bucket"
              stroke="#687166"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: '#262D26' }}
              tick={{ fill: '#687166', fontFamily: 'monospace' }}
            />
            <YAxis
              stroke="#687166"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: '#262D26' }}
              tick={{ fill: '#687166', fontFamily: 'monospace' }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="p-2.5 rounded bg-[#181E18] border border-[#262D26] shadow-elevated text-xs font-mono">
                      <div className="text-[#929B90]">Band: {payload[0].payload.bucket}</div>
                      <div className="text-[#F2F4EF] font-bold mt-1">
                        {payload[0].value?.toLocaleString()} transactions
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[2, 2, 0, 0]} isAnimationActive={false}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
