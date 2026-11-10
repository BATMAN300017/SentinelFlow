'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ArrowLeftRight,
  ShieldAlert,
  Briefcase,
  Network,
  Users,
  BrainCircuit,
  Cpu,
  FileCode2,
  ScrollText,
  Settings,
  Shield,
  Workflow,
  X,
} from 'lucide-react';
import { APP_NAME, APP_TAGLINE, NAVIGATION_SECTIONS } from '@/lib/constants';

const ICON_MAP: Record<string, React.ReactNode> = {
  LayoutDashboard: <LayoutDashboard className="w-4 h-4 shrink-0" />,
  ArrowLeftRight: <ArrowLeftRight className="w-4 h-4 shrink-0" />,
  ShieldAlert: <ShieldAlert className="w-4 h-4 shrink-0" />,
  Briefcase: <Briefcase className="w-4 h-4 shrink-0" />,
  Network: <Network className="w-4 h-4 shrink-0" />,
  Users: <Users className="w-4 h-4 shrink-0" />,
  BrainCircuit: <BrainCircuit className="w-4 h-4 shrink-0" />,
  Cpu: <Cpu className="w-4 h-4 shrink-0" />,
  FileCode2: <FileCode2 className="w-4 h-4 shrink-0" />,
  ScrollText: <ScrollText className="w-4 h-4 shrink-0" />,
  Settings: <Settings className="w-4 h-4 shrink-0" />,
  Workflow: <Workflow className="w-4 h-4 shrink-0" />,
};

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#0D100D] border-r border-[#262D26] select-none text-[#F2F4EF]">
      {/* Brand Header */}
      <div className="px-5 py-4 border-b border-[#262D26] flex items-center justify-between">
        <Link
          href="/dashboard"
          onClick={onClose}
          className="flex items-center space-x-3 group"
          title="SentinelFlow Platform Home"
        >
          <div className="w-8 h-8 rounded bg-[#121612] border border-[#262D26] flex items-center justify-center text-[#B7F34A] group-hover:border-[#B7F34A]/50 transition-colors">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold tracking-wider font-mono text-[#F2F4EF] uppercase group-hover:text-white transition-colors">
                {APP_NAME}
              </span>
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-[#181E18] text-[#B7F34A] border border-[#262D26] font-mono">
                INSTITUTIONAL
              </span>
            </div>
            <div className="text-[10px] text-[#687166] font-mono tracking-tight truncate max-w-[150px]">
              {APP_TAGLINE}
            </div>
          </div>
        </Link>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-1.5 rounded text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#181E18] transition"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {NAVIGATION_SECTIONS.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-2 text-[9px] font-bold font-mono text-[#687166] tracking-widest uppercase">
              {section.title}
            </div>
            <div className="space-y-0.5 pt-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={`flex items-center justify-between px-2.5 py-2 rounded text-xs font-mono font-medium transition-all ${
                      isActive
                        ? 'bg-[#181E18] text-[#F2F4EF] border-l-2 border-[#B7F34A] pl-2 border-y border-r border-[#262D26]'
                        : 'text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#121612] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      <span className={isActive ? 'text-[#B7F34A]' : 'text-[#687166]'}>
                        {ICON_MAP[item.icon]}
                      </span>
                      <span className="truncate">{item.name}</span>
                    </div>
                    {isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#B7F34A] shrink-0" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Status Telemetry */}
      <div className="p-3 border-t border-[#262D26] bg-[#0A0D0A] space-y-2">
        <div className="p-2.5 rounded bg-[#121612] border border-[#262D26] space-y-1.5">
          <div className="flex items-center justify-between text-[10px] font-mono">
            <span className="flex items-center space-x-1.5 text-[#929B90]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#B7F34A]" />
              <span>Surveillance Engine</span>
            </span>
            <span className="text-[#B7F34A] font-bold text-[9px] px-1 py-0.2 rounded bg-[#142010] border border-[#29421E]">
              ONLINE
            </span>
          </div>
          <div className="text-[9px] text-[#687166] font-mono truncate">
            Edge Ingestion • Real-Time Scoring
          </div>
        </div>
        <div className="text-[9px] text-[#414840] font-mono text-center">
          SentinelFlow Financial Intelligence v2.1
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col h-screen">
        {sidebarContent}
      </aside>

      {/* Mobile Navigation Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="fixed inset-0 bg-[#080A08]/85 backdrop-blur-sm transition-opacity"
            onClick={onClose}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 w-72 max-w-[85vw] flex flex-col shadow-2xl animate-fade-in">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
