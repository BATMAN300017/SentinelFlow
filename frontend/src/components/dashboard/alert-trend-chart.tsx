'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface AlertTrendChartProps {
  totalAlerts?: number;
}

const MOCK_ALERT_TREND = [
  { day: 'Mon', critical: 12, high: 28, medium: 45 },
  { day: 'Tue', critical: 15, high: 32, medium: 41 },
  { day: 'Wed', critical: 8, high: 22, medium: 39 },
  { day: 'Thu', critical: 18, high: 35, medium: 52 },
  { day: 'Fri', critical: 14, high: 30, medium: 48 },
  { day: 'Sat', critical: 6, high: 18, medium: 26 },
  { day: 'Sun', critical: 9, high: 20, medium: 31 },
];

export function AlertTrendChart({ totalAlerts }: AlertTrendChartProps) {
  return (
    <div className="p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26]">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF]">
            Alert Generation Velocity by Severity Tier
          </h3>
          <p className="text-[11px] text-[#687166] font-mono mt-0.5">
            7-day rolling window of triage escalations
          </p>
        </div>
        <div className="flex items-center space-x-4 text-[11px] font-mono">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#FF4D4D]" />
            <span className="text-[#929B90]">Critical</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#FF8833]" />
            <span className="text-[#929B90]">High</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#FFB800]" />
            <span className="text-[#929B90]">Medium</span>
          </div>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={MOCK_ALERT_TREND} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="day"
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
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="p-2.5 rounded bg-[#181E18] border border-[#262D26] shadow-elevated text-xs font-mono space-y-1">
                      <div className="text-[#929B90] font-bold">{payload[0].payload.day} Triage Volume</div>
                      {payload.map((p: any) => (
                        <div key={p.name} className="flex items-center justify-between space-x-3">
                          <span className="capitalize text-[#929B90]">{p.name}:</span>
                          <span className="font-bold text-[#F2F4EF] tabular-nums">{p.value}</span>
                        </div>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Line
              type="monotone"
              dataKey="critical"
              stroke="#FF4D4D"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="high"
              stroke="#FF8833"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="medium"
              stroke="#FFB800"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
