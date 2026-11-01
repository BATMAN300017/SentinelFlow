'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { Shield, ShieldAlert, ArrowRight, LayoutDashboard, ArrowLeftRight, ShieldAlert as AlertIcon, Network } from 'lucide-react';
import { APP_NAME, APP_TAGLINE } from '@/lib/constants';

export default function NotFound() {
  useEffect(() => {
    document.title = '404 - Record Not Found | SentinelFlow AI';
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 sm:p-12 font-sans select-none relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header with Clickable Logo */}
      <header className="flex items-center justify-between z-10">
        <Link href="/dashboard" className="flex items-center space-x-3 group">
          <div className="p-2 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20 group-hover:scale-105 transition-transform">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wider font-mono text-slate-100 group-hover:text-sky-300 transition-colors flex items-center space-x-1.5">
              <span>{APP_NAME}</span>
              <span className="text-[10px] px-1 py-0.2 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-mono">
                v2.0
              </span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono tracking-tight">
              {APP_TAGLINE}
            </div>
          </div>
        </Link>
        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400">
          HTTP 404
        </span>
      </header>

      {/* Main 404 Card */}
      <main className="max-w-xl mx-auto my-auto text-center space-y-6 z-10 py-12">
        <div className="inline-flex p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-rose-400 shadow-xl shadow-rose-950/20 animate-pulse">
          <ShieldAlert className="w-12 h-12" />
        </div>

        <div className="space-y-2">
          <div className="text-xs font-mono font-bold uppercase tracking-widest text-sky-400">
            Route Exception &bull; Code 404
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold font-mono text-slate-100 tracking-tight">
            Surveillance Record Not Found
          </h1>
          <p className="text-xs sm:text-sm font-mono text-slate-400 max-w-md mx-auto leading-relaxed">
            The requested transaction hash, investigation case dossier, or fund-flow entity route does not exist or has been purged from active telemetry.
          </p>
        </div>

        {/* Quick Recovery Navigation */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left">
          <Link
            href="/dashboard"
            className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-sky-500/40 transition group flex items-center justify-between"
          >
            <div className="flex items-center space-x-2.5">
              <LayoutDashboard className="w-4 h-4 text-sky-400" />
              <div>
                <div className="text-xs font-bold font-mono text-slate-200 group-hover:text-sky-300">
                  Command Center
                </div>
                <div className="text-[10px] font-mono text-slate-500">Live multi-signal telemetry</div>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-sky-400 group-hover:translate-x-0.5 transition-all" />
          </Link>

          <Link
            href="/transactions"
            className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-emerald-500/40 transition group flex items-center justify-between"
          >
            <div className="flex items-center space-x-2.5">
              <ArrowLeftRight className="w-4 h-4 text-emerald-400" />
              <div>
                <div className="text-xs font-bold font-mono text-slate-200 group-hover:text-emerald-300">
                  Live Transactions
                </div>
                <div className="text-[10px] font-mono text-slate-500">482,810 active records</div>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all" />
          </Link>

          <Link
            href="/alerts"
            className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-amber-500/40 transition group flex items-center justify-between"
          >
            <div className="flex items-center space-x-2.5">
              <AlertIcon className="w-4 h-4 text-amber-400" />
              <div>
                <div className="text-xs font-bold font-mono text-slate-200 group-hover:text-amber-300">
                  Alerts Queue
                </div>
                <div className="text-[10px] font-mono text-slate-500">Triage & route maps</div>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all" />
          </Link>

          <Link
            href="/fund-flow"
            className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-purple-500/40 transition group flex items-center justify-between"
          >
            <div className="flex items-center space-x-2.5">
              <Network className="w-4 h-4 text-purple-400" />
              <div>
                <div className="text-xs font-bold font-mono text-slate-200 group-hover:text-purple-300">
                  Fund Flow Tracing
                </div>
                <div className="text-[10px] font-mono text-slate-500">Multi-hop money flows</div>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-0.5 transition-all" />
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center text-[11px] font-mono text-slate-600 z-10 pt-6 border-t border-slate-900">
        &copy; 2026 SentinelFlow AI &bull; Autonomous Financial Crime Intelligence &bull; All rights reserved
      </footer>
    </div>
  );
}
