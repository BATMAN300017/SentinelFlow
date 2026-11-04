'use client';

import React, { useEffect, useState } from 'react';
import { pingApi } from '@/lib/api-client';
import { usePermissions } from '@/hooks/use-permissions';
import { UserRole } from '@/lib/auth';
import { Activity, ShieldCheck, Wifi, WifiOff, Search, User, Menu } from 'lucide-react';

interface TopbarProps {
  onOpenCommandPalette?: () => void;
  onToggleMobileMenu?: () => void;
}

export function Topbar({ onOpenCommandPalette, onToggleMobileMenu }: TopbarProps) {
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
    <header className="h-13 border-b border-slate-800/80 bg-[#0B0F17]/95 backdrop-blur-sm px-4 sm:px-6 flex items-center justify-between z-20">
      {/* Left: Mobile Menu Toggle & Search Trigger */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="md:hidden p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-900 border border-slate-800 transition"
            aria-label="Toggle navigation drawer"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center space-x-2 px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-mono text-slate-400 bg-slate-900/80 border border-slate-800 hover:border-slate-700 hover:text-slate-200 transition"
        >
          <Search className="w-3.5 h-3.5 shrink-0 text-slate-500" />
          <span className="hidden sm:inline">Search accounts, transactions, cases...</span>
          <span className="sm:hidden text-[11px]">Search...</span>
          <kbd className="hidden sm:inline-block text-[10px] px-1.5 py-0.5 rounded bg-slate-800/70 text-slate-400 border border-slate-700/60">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: API Connectivity Pill + User Session */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* API Status Pill */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 px-2 sm:px-2.5 py-1 rounded text-[10px] sm:text-[11px] font-mono border bg-slate-900/60 border-slate-800/80">
          {apiStatus.checked ? (
            apiStatus.ok ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="text-emerald-400 font-medium hidden xs:inline sm:inline">API Connected</span>
                <span className="text-emerald-400 font-medium xs:hidden">Online</span>
                <span className="text-slate-500 hidden md:inline tabular-nums">({apiStatus.latencyMs}ms)</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-rose-400 shrink-0" />
                <span className="text-rose-400 font-medium">Reconnecting</span>
              </>
            )
          ) : (
            <>
              <Activity className="w-3 h-3 text-slate-400 animate-spin shrink-0" />
              <span className="text-slate-400 hidden sm:inline">Checking API...</span>
            </>
          )}
        </div>

        {/* Environment Pill */}
        <div className="hidden lg:inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-900 text-slate-400 border border-slate-800">
          PROD-WORKSTATION
        </div>

        {/* User Role Switcher & Profile */}
        <div className="flex items-center space-x-2.5 pl-2.5 border-l border-slate-800/80">
          <a
            href={`mailto:${user.email}`}
            title={`Logged in as ${user.name} (${user.email})`}
            className="w-6.5 h-6.5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[11px] font-bold font-mono text-slate-200 hover:text-emerald-300 transition shrink-0"
          >
            {user.avatarInitials}
          </a>
          <div className="text-left hidden md:block">
            <a
              href={`mailto:${user.email}`}
              className="text-xs font-semibold text-slate-200 leading-none hover:text-emerald-400 transition block truncate max-w-[120px]"
              title={`Send email to ${user.email}`}
            >
              {user.name}
            </a>
            <select
              value={role}
              onChange={(e) => switchRole(e.target.value as UserRole)}
              className="mt-0.5 text-[10px] font-mono bg-transparent text-slate-400 hover:text-emerald-400 border-none p-0 focus:outline-none cursor-pointer"
            >
              <option value="SENIOR_INVESTIGATOR" className="bg-[#0B0F17] text-slate-200">
                Senior Investigator
              </option>
              <option value="INVESTIGATOR" className="bg-[#0B0F17] text-slate-200">
                Investigator
              </option>
              <option value="FRAUD_ADMIN" className="bg-[#0B0F17] text-slate-200">
                Fraud Admin
              </option>
              <option value="AUDITOR" className="bg-[#0B0F17] text-slate-200">
                Auditor (Read-Only)
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
