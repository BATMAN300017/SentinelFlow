'use client';

import React, { useState } from 'react';
import { Sidebar } from './sidebar';
import { Topbar } from './topbar';
import { Breadcrumb } from './breadcrumb';
import { CommandPalette } from './command-palette';
import { ToastProvider } from '@/components/shared/toast';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <ToastProvider>
      <div className="flex h-screen w-full max-w-full overflow-hidden bg-slate-950 text-slate-100 antialiased font-sans">
        <Sidebar isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
        <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
          <Topbar
            onOpenCommandPalette={() => setCommandPaletteOpen(true)}
            onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
          />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 md:p-8 bg-slate-900/40">
            <Breadcrumb />
            {children}
          </main>
        </div>
        <CommandPalette
          isOpen={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
        />
      </div>
    </ToastProvider>
  );
}
