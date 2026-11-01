'use client';

import React, { useEffect, useState } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { pingApi } from '@/lib/api-client';
import { API_BASE_URL } from '@/lib/utils';
import { Settings, Server, Shield, Database, Lock } from 'lucide-react';

export default function SettingsPage() {
  const [apiHealth, setApiHealth] = useState<any>(null);

  useEffect(() => {
    document.title = 'System Configuration & Architecture | SentinelFlow AI';
    async function check() {
      const res = await pingApi();
      setApiHealth(res);
    }
    check();
  }, []);

  return (
    <AppShell>
      <head>
        <title>System Configuration &amp; Architecture | SentinelFlow AI</title>
        <meta name="description" content="Technical runtime architecture, canonical Cloudflare frontend, Render FastAPI backend connectivity, and ensemble model weights." />
      </head>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold font-mono text-slate-100 tracking-tight flex items-center space-x-3">
            <span>System Configuration & Architecture</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 font-mono mt-1">
            Canonical frontend, Render backend routing, and calibrated model weight parameters.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Cloudflare Frontend Topology */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-sky-950 border border-sky-800 text-sky-400">
                <Server className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold font-mono text-slate-100">
                Canonical Frontend Runtime
              </h3>
            </div>
            <div className="space-y-2 text-xs font-mono text-slate-300">
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">Hosting Provider:</span>
                <span className="text-sky-400 font-bold">Cloudflare Pages / Workers</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">Framework:</span>
                <span className="text-slate-200">Next.js 14 Static Export</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">SPA Fallback:</span>
                <span className="text-emerald-400 font-bold">Native 200.html / single-page-application</span>
              </div>
            </div>
          </div>

          {/* Render Backend API Topology */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-purple-950 border border-purple-800 text-purple-400">
                <Database className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold font-mono text-slate-100">
                Production Backend API
              </h3>
            </div>
            <div className="space-y-2 text-xs font-mono text-slate-300">
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">Render API URL:</span>
                <span className="text-slate-200 truncate max-w-[220px]" title={API_BASE_URL}>
                  {API_BASE_URL}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">Connection Status:</span>
                <span className={`font-bold ${apiHealth?.ok ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {apiHealth?.ok ? `Connected (${apiHealth.latencyMs}ms)` : 'Probing...'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-850">
                <span className="text-slate-500">Persistent Database:</span>
                <span className="text-emerald-400 font-bold">Supabase PostgreSQL</span>
              </div>
            </div>
          </div>
        </div>

        {/* Ensemble Weight Configuration */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-sky-400" />
            <h3 className="text-sm font-bold font-mono text-slate-100">
              Multi-Signal Detection Ensemble Weights
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
              <span className="text-slate-500 text-[10px]">Deterministic Rules</span>
              <div className="text-lg font-bold text-sky-400">30%</div>
              <p className="text-[10px] text-slate-500">Heuristic boundaries</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
              <span className="text-slate-500 text-[10px]">Behavioral MAD</span>
              <div className="text-lg font-bold text-emerald-400">25%</div>
              <p className="text-[10px] text-slate-500">Statistical dispersion</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
              <span className="text-slate-500 text-[10px]">Supervised Models</span>
              <div className="text-lg font-bold text-purple-400">25%</div>
              <p className="text-[10px] text-slate-500">Forest consensus</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-1">
              <span className="text-slate-500 text-[10px]">Graph Intelligence</span>
              <div className="text-lg font-bold text-indigo-400">20%</div>
              <p className="text-[10px] text-slate-500">Mule chains & cycles</p>
            </div>
          </div>
        {/* Operational Contacts & Governance Support */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
          <div className="flex items-center space-x-2">
            <Lock className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-bold font-mono text-slate-100">
              Operational Governance &amp; Security Contacts
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-2">
              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                Financial Crime Operations Desk
              </span>
              <div className="space-y-1">
                <div>
                  <span className="text-slate-400">Incident Hotline: </span>
                  <a
                    href="tel:+18005550199"
                    className="text-emerald-400 hover:text-emerald-300 underline font-semibold transition"
                  >
                    +1 (800) 555-0199
                  </a>
                </div>
                <div>
                  <span className="text-slate-400">Dispatch Email: </span>
                  <a
                    href="mailto:operations@sentinelflow.bank"
                    className="text-sky-400 hover:text-sky-300 underline transition"
                  >
                    operations@sentinelflow.bank
                  </a>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-2">
              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                Compliance &amp; Model Governance
              </span>
              <div className="space-y-1">
                <div>
                  <span className="text-slate-400">Audit Hotline: </span>
                  <a
                    href="tel:+18005550188"
                    className="text-emerald-400 hover:text-emerald-300 underline font-semibold transition"
                  >
                    +1 (800) 555-0188
                  </a>
                </div>
                <div>
                  <span className="text-slate-400">Governance Email: </span>
                  <a
                    href="mailto:compliance@sentinelflow.bank"
                    className="text-sky-400 hover:text-sky-300 underline transition"
                  >
                    compliance@sentinelflow.bank
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* System Copyright & Governance Notice */}
        <div className="text-center py-4 border-t border-slate-850 text-xs font-mono text-slate-500">
          &copy; 2026 SentinelFlow AI &bull; Autonomous Financial Crime Intelligence Platform &bull; All rights reserved.
        </div>
      </div>
    </AppShell>
  );
}
