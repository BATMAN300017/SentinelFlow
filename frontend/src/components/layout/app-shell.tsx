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
      <div className="flex h-screen w-full max-w-full overflow-hidden bg-[#080A08] text-[#F2F4EF] antialiased font-sans">
        <Sidebar isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
        <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden bg-[#080A08]">
          <Topbar
            onOpenCommandPalette={() => setCommandPaletteOpen(true)}
            onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
          />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 lg:p-7 bg-[#080A08]">
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
