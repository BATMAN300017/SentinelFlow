'use client';

import React from 'react';
import { TimelineEvent } from '@/types/investigation';
import { Clock, ShieldAlert, CheckCircle, FileText } from 'lucide-react';

interface CaseTimelineProps {
  events?: TimelineEvent[];
}

export function CaseTimeline({ events = [] }: CaseTimelineProps) {
  const defaultEvents: TimelineEvent[] = events.length > 0 ? events : [
    {
      id: 'EVT-1',
      timestamp: 'Today, 04:12 UTC',
      title: 'Statistical Velocity Spike Flagged',
      description: 'MAD anomaly engine scored outbound IMPS volume at 89/100.',
      actor: 'SentinelFlow Autonomous Detector',
      category: 'DETECTION',
    },
    {
      id: 'EVT-2',
      timestamp: 'Today, 04:15 UTC',
      title: 'Case Auto-Provisioned',
      description: 'Correlation engine grouped 4 linked transactions under CASE-2026-60C23.',
      actor: 'System Pipeline',
      category: 'ACTION',
    },
    {
      id: 'EVT-3',
      timestamp: 'Today, 05:30 UTC',
      title: 'Triage Analyst Assigned',
      description: 'Senior Investigator Sarah Chen accepted primary investigative responsibility.',
      actor: 'Sarah Chen',
      category: 'ACTION',
    },
  ];

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <h3 className="text-sm font-semibold text-slate-100 font-mono">Case Activity Timeline</h3>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {defaultEvents.map((ev) => (
          <div key={ev.id} className="relative space-y-1">
            <span className="absolute -left-[27px] top-1 w-3 h-3 rounded-full bg-sky-500 border-2 border-slate-900" />
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-slate-200">{ev.title}</span>
              <span className="text-slate-500">{ev.timestamp}</span>
            </div>
            <p className="text-xs font-mono text-slate-400">{ev.description}</p>
            <div className="text-[10px] font-mono text-slate-500">By: {ev.actor}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
