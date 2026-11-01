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

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 flex flex-col h-screen bg-slate-950 border-r border-slate-850 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-850 flex items-center space-x-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-wider font-mono text-slate-100 flex items-center space-x-1.5">
            <span>{APP_NAME}</span>
            <span className="text-[10px] px-1 py-0.2 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-mono">
              v2.0
            </span>
          </div>
          <div className="text-[11px] text-slate-500 font-mono tracking-tight truncate max-w-[145px]">
            {APP_TAGLINE}
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {SECTIONS.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-3 text-[10px] font-bold font-mono text-slate-500 tracking-widest uppercase">
              {section.title}
            </div>
            <div className="space-y-0.5 pt-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                      isActive
                        ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                    }`}
                  >
                    <span className={isActive ? 'text-sky-400' : 'text-slate-500'}>
                      {ICON_MAP[item.icon]}
                    </span>
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Telemetry Footer */}
      <div className="p-3 border-t border-slate-850 bg-slate-950/70">
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span className="flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>Surveillance Engine</span>
            </span>
            <span className="text-emerald-400 font-bold">ONLINE</span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Canonical Cloudflare App • Render API
          </div>
        </div>
      </div>
    </aside>
  );
}
