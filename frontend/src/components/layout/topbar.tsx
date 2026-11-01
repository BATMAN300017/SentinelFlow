'use client';

import React, { useEffect, useState } from 'react';
import { pingApi } from '@/lib/api-client';
import { usePermissions } from '@/hooks/use-permissions';
import { UserRole } from '@/lib/auth';
import { Activity, ShieldCheck, Wifi, WifiOff, Search, User } from 'lucide-react';

interface TopbarProps {
  onOpenCommandPalette?: () => void;
}

export function Topbar({ onOpenCommandPalette }: TopbarProps) {
  const { user, role, switchRole } = usePermissions();
  const [apiStatus, setApiStatus] = useState<{
    ok: boolean;
    latencyMs: number;
    checked: boolean;
  }>({ ok: false, latencyMs: 0, checked: false });

  useEffect(() => {
    async function checkHealth() {
      const res = await pingApi();
      setApiStatus({ ok: res.ok, latencyMs: res.latencyMs, checked: true });
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 border-b border-slate-850 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between z-20">
      {/* Left: Search Trigger */}
      <div className="flex items-center space-x-4">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:text-slate-200 transition"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Quick search cases, transactions...</span>
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: API Connectivity Pill + User Session */}
      <div className="flex items-center space-x-4">
        {/* API Status Pill */}
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full text-[11px] font-mono border bg-slate-900 border-slate-800">
          {apiStatus.checked ? (
            apiStatus.ok ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                <span className="text-emerald-400 font-medium">Render API Connected</span>
                <span className="text-slate-500">({apiStatus.latencyMs}ms)</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-rose-400" />
                <span className="text-rose-400 font-medium">API Connecting...</span>
              </>
            )
          ) : (
            <>
              <Activity className="w-3 h-3 text-sky-400 animate-spin" />
              <span className="text-slate-400">Pinging backend...</span>
            </>
          )}
        </div>

        {/* Environment Pill */}
        <div className="hidden sm:inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-950/80 text-sky-400 border border-sky-800/80">
          PROD-CALIBRATED
        </div>

        {/* User Role Switcher */}
        <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-xs font-bold font-mono text-white">
            {user.avatarInitials}
          </div>
          <div className="text-left hidden md:block">
            <div className="text-xs font-semibold text-slate-200 leading-none">{user.name}</div>
            <select
              value={role}
              onChange={(e) => switchRole(e.target.value as UserRole)}
              className="mt-0.5 text-[10px] font-mono bg-transparent text-slate-400 hover:text-sky-400 border-none p-0 focus:outline-none cursor-pointer"
            >
              <option value="SENIOR_INVESTIGATOR" className="bg-slate-900 text-slate-200">
                Senior Investigator
              </option>
              <option value="INVESTIGATOR" className="bg-slate-900 text-slate-200">
                Investigator
              </option>
              <option value="FRAUD_ADMIN" className="bg-slate-900 text-slate-200">
                Fraud Admin
              </option>
              <option value="AUDITOR" className="bg-slate-900 text-slate-200">
                Auditor (Read-Only)
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
