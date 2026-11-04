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
  Activity,
  Workflow,
  X,
} from 'lucide-react';
import { APP_NAME, APP_TAGLINE } from '@/lib/constants';

const ICON_MAP: Record<string, React.ReactNode> = {
  LayoutDashboard: <LayoutDashboard className="w-4 h-4" />,
  ArrowLeftRight: <ArrowLeftRight className="w-4 h-4" />,
  ShieldAlert: <ShieldAlert className="w-4 h-4" />,
  Briefcase: <Briefcase className="w-4 h-4" />,
  Network: <Network className="w-4 h-4" />,
  Users: <Users className="w-4 h-4" />,
  BrainCircuit: <BrainCircuit className="w-4 h-4" />,
  Cpu: <Cpu className="w-4 h-4" />,
  FileCode2: <FileCode2 className="w-4 h-4" />,
  ScrollText: <ScrollText className="w-4 h-4" />,
  Settings: <Settings className="w-4 h-4" />,
  Workflow: <Workflow className="w-4 h-4" />,
};

const SECTIONS = [
  {
    title: 'OPERATIONS',
    items: [
      { name: 'Command Center', href: '/dashboard', icon: 'LayoutDashboard' },
      { name: 'Live Transactions', href: '/transactions', icon: 'ArrowLeftRight' },
      { name: 'Alerts Queue', href: '/alerts', icon: 'ShieldAlert' },
      { name: 'Investigations', href: '/investigations', icon: 'Briefcase' },
    ],
  },
  {
    title: 'SURVEILLANCE & GRAPH',
    items: [
      { name: 'Fund Flow Tracing', href: '/fund-flow', icon: 'Workflow' },
      { name: 'Network Intelligence', href: '/network', icon: 'Network' },
      { name: 'Entity Profiles', href: '/entities', icon: 'Users' },
    ],
  },
  {
    title: 'MACHINE LEARNING & AUDIT',
    items: [
      { name: 'Model Intelligence', href: '/intelligence', icon: 'BrainCircuit' },
      { name: 'Model Learning', href: '/feedback', icon: 'Cpu' },
      { name: 'Detection Rules', href: '/rules', icon: 'FileCode2' },
      { name: 'Audit Trail', href: '/audit', icon: 'ScrollText' },
    ],
  },
  {
    title: 'CONFIGURATION',
    items: [{ name: 'System Settings', href: '/settings', icon: 'Settings' }],
  },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#0B0F17] border-r border-slate-800/80 select-none">
      {/* Brand Header - Clickable Logo & Title to Dashboard */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <Link
          href="/dashboard"
          onClick={onClose}
          className="flex items-center space-x-3 group transition"
          title="Go to SentinelFlow Command Center"
        >
          <div className="p-2 rounded-lg bg-slate-900 border border-emerald-500/30 text-emerald-400 group-hover:border-emerald-500/60 transition-colors">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold tracking-wider font-mono text-slate-100 flex items-center space-x-1.5 group-hover:text-emerald-300 transition-colors">
              <span>{APP_NAME}</span>
              <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-mono">
                v2.0
              </span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono tracking-tight truncate max-w-[145px]">
              {APP_TAGLINE}
            </div>
          </div>
        </Link>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition"
            aria-label="Close navigation menu"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-3 space-y-5">
        {SECTIONS.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-2.5 text-[9px] font-bold font-mono text-slate-500 tracking-wider uppercase">
              {section.title}
            </div>
            <div className="space-y-0.5 pt-0.5">
              {section.items.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/70 border border-transparent'
                    }`}
                  >
                    <span className={isActive ? 'text-emerald-400' : 'text-slate-500'}>
                      {ICON_MAP[item.icon]}
                    </span>
                    <span className="truncate">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Telemetry & Copyright Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-[#0B0F17] space-y-2">
        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1">
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span className="flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Surveillance Engine</span>
            </span>
            <span className="text-emerald-400 font-bold text-[9px]">ONLINE</span>
          </div>
          <div className="text-[9px] text-slate-500 font-mono">
            Workers Static Assets • Render API
          </div>
        </div>
        <div className="text-[9px] text-slate-600 font-mono text-center">
          &copy; 2026 SentinelFlow AI
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

      {/* Mobile Drawer Navigation */}
      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
            onClick={onClose}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="fixed inset-y-0 left-0 w-72 max-w-[85vw] flex flex-col shadow-2xl animate-fade-in">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
