'use client';

import React, { useEffect } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import Link from 'next/link';
import { ShieldAlert, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function ReviewQueuePage() {
  useEffect(() => {
    document.title = 'Analyst Review & Triage Queue | SentinelFlow AI';
  }, []);

  return (
    <AppShell>
      <head>
        <title>Analyst Review &amp; Triage Queue | SentinelFlow AI</title>
        <meta name="description" content="Senior investigator review queue for incident dispositioning, peer approvals, and regulatory filing triage." />
      </head>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
            <span>Analyst Review Queue</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-800">
              Triage & Peer Approval
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
            Prioritized queue of incidents requiring senior investigator sign-off before regulatory filing.
          </p>
        </div>

        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-amber-950 border border-amber-800 text-amber-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold font-mono text-slate-100">
                Peer Review & Adjudication Gateway
              </h3>
              <p className="text-xs font-mono text-slate-400">
                Supervisory sign-off ensures compliance with regulatory Suspicious Activity Reporting thresholds.
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-850 flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">Active alerts awaiting triage:</span>
            <Link
              href="/alerts"
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-sky-600 hover:bg-sky-500 text-white transition shadow-lg shadow-sky-600/20"
            >
              <span>Open Alerts Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
