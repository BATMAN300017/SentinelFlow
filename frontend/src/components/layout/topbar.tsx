'use client';

import React, { useEffect, useState } from 'react';
import { pingApi } from '@/lib/api-client';
import { usePermissions } from '@/hooks/use-permissions';
import { UserRole } from '@/lib/auth';
import { Activity, WifiOff, Search, Menu } from 'lucide-react';

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
    <header className="h-13 border-b border-[#262D26] bg-[#0D100D] px-4 sm:px-6 flex items-center justify-between z-20 shrink-0">
      {/* Left: Mobile Menu Toggle & Command Palette Trigger */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="md:hidden p-1.5 rounded text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#181E18] border border-[#262D26] transition"
            aria-label="Toggle navigation drawer"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono text-[#929B90] bg-[#121612] border border-[#262D26] hover:border-[#323B32] hover:text-[#F2F4EF] transition"
        >
          <Search className="w-3.5 h-3.5 shrink-0 text-[#687166]" />
          <span className="hidden sm:inline">Search accounts, transactions, cases...</span>
          <span className="sm:hidden text-[11px]">Search...</span>
          <kbd className="hidden sm:inline-block text-[10px] px-1.5 py-0.5 rounded bg-[#181E18] text-[#929B90] border border-[#262D26]">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: API Telemetry & User Controls */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Status Indicator */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 px-2.5 py-1 rounded text-[10px] sm:text-[11px] font-mono border bg-[#121612] border-[#262D26]">
          {apiStatus.checked ? (
            apiStatus.ok ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-[#B7F34A] shrink-0" />
                <span className="text-[#F2F4EF] font-medium hidden xs:inline sm:inline">API Connected</span>
                <span className="text-[#F2F4EF] font-medium xs:hidden">Online</span>
                <span className="text-[#687166] hidden md:inline tabular-nums">({apiStatus.latencyMs}ms)</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-[#FF4D4D] shrink-0" />
                <span className="text-[#FF4D4D] font-medium">Offline</span>
              </>
            )
          ) : (
            <>
              <Activity className="w-3 h-3 text-[#687166] animate-spin shrink-0" />
              <span className="text-[#687166] hidden sm:inline">Checking telemetry...</span>
            </>
          )}
        </div>

        {/* Security Classification */}
        <div className="hidden lg:inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#121612] text-[#929B90] border border-[#262D26]">
          INSTITUTIONAL AML
        </div>

        {/* User Role Switcher */}
        <div className="flex items-center space-x-2.5 pl-2.5 border-l border-[#262D26]">
          <div
            title={`Session: ${user.name} (${user.email})`}
            className="w-7 h-7 rounded bg-[#181E18] border border-[#262D26] flex items-center justify-center text-[11px] font-bold font-mono text-[#F2F4EF] shrink-0"
          >
            {user.avatarInitials}
          </div>
          <div className="text-left hidden md:block">
            <div className="text-xs font-semibold text-[#F2F4EF] leading-none block truncate max-w-[120px]">
              {user.name}
            </div>
            <select
              value={role}
              onChange={(e) => switchRole(e.target.value as UserRole)}
              className="mt-0.5 text-[10px] font-mono bg-transparent text-[#929B90] hover:text-[#B7F34A] border-none p-0 focus:outline-none cursor-pointer"
            >
              <option value="SENIOR_INVESTIGATOR" className="bg-[#0D100D] text-[#F2F4EF]">
                Senior Investigator
              </option>
              <option value="INVESTIGATOR" className="bg-[#0D100D] text-[#F2F4EF]">
                Investigator
              </option>
              <option value="FRAUD_ADMIN" className="bg-[#0D100D] text-[#F2F4EF]">
                Risk Administrator
              </option>
              <option value="AUDITOR" className="bg-[#0D100D] text-[#F2F4EF]">
                Compliance Auditor
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
