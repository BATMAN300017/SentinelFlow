'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0 || pathname === '/dashboard') {
    return null;
  }

  return (
    <nav className="flex items-center space-x-2 text-xs font-mono text-slate-400 mb-4 select-none">
      <Link href="/dashboard" className="flex items-center hover:text-sky-400 transition">
        <Home className="w-3.5 h-3.5" />
      </Link>
      {segments.map((seg, idx) => {
        const href = `/${segments.slice(0, idx + 1).join('/')}`;
        const isLast = idx === segments.length - 1;
        const formatted = seg.charAt(0).toUpperCase() + seg.slice(1);

        return (
          <React.Fragment key={href}>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            {isLast ? (
              <span className="text-slate-200 font-semibold">{formatted}</span>
            ) : (
              <Link href={href} className="hover:text-sky-400 transition">
                {formatted}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
