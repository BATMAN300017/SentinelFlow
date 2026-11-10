'use client';

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface TransactionVolumeChartProps {
  throughputTpm?: number;
}

const MOCK_SERIES = [
  { time: '00:00', volume: 4120 },
  { time: '02:00', volume: 2980 },
  { time: '04:00', volume: 2150 },
  { time: '06:00', volume: 3410 },
  { time: '08:00', volume: 6890 },
  { time: '10:00', volume: 9240 },
  { time: '12:00', volume: 11450 },
  { time: '14:00', volume: 10890 },
  { time: '16:00', volume: 12340 },
  { time: '18:00', volume: 11120 },
  { time: '20:00', volume: 8450 },
  { time: '22:00', volume: 5670 },
];

export function TransactionVolumeChart({ throughputTpm = 0 }: TransactionVolumeChartProps) {
  return (
    <div className="p-4 sm:p-5 rounded bg-[#121612] border border-[#262D26]">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF]">
            Transactional Surveillance Throughput
          </h3>
          <p className="text-[11px] text-[#687166] font-mono mt-0.5">
            24-hour continuous surveillance ingestion profile
          </p>
        </div>
        <div className="flex items-center space-x-2 text-[11px] font-mono">
          <span className="text-[#929B90]">Live Rate:</span>
          <span className="text-[#B7F34A] font-bold tabular-nums">
            {throughputTpm > 0 ? throughputTpm.toLocaleString() : '842'} TPM
          </span>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={MOCK_SERIES} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="volGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#B7F34A" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#B7F34A" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
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
                      <div className="text-[#929B90]">{payload[0].payload.time} UTC</div>
                      <div className="text-[#F2F4EF] font-bold mt-1">
                        {payload[0].value?.toLocaleString()} txns
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="volume"
              stroke="#B7F34A"
              strokeWidth={1.5}
              fill="url(#volGradient)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
