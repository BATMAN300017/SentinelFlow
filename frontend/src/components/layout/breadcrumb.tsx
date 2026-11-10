'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Intelligence Overview',
  transactions: 'Live Transactions',
  alerts: 'Alerts Queue',
  investigations: 'Investigation Workspace',
  'fund-flow': 'Fund Flow Tracing',
  network: 'Network Intelligence',
  entities: 'Entity Profiles',
  intelligence: 'Model Intelligence',
  feedback: 'Model Learning & Calibration',
  rules: 'Detection Rules',
  audit: 'Audit Log',
  settings: 'System Configuration',
};

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0 || pathname === '/dashboard') {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center space-x-1.5 text-xs font-mono text-[#687166]">
      <Link
        href="/dashboard"
        className="flex items-center space-x-1 text-[#929B90] hover:text-[#F2F4EF] transition-colors"
      >
        <Home className="w-3.5 h-3.5" />
        <span>Workstation</span>
      </Link>
      {segments.map((segment, index) => {
        const href = `/${segments.slice(0, index + 1).join('/')}`;
        const isLast = index === segments.length - 1;
        const label = ROUTE_LABELS[segment] || segment.replace(/-/g, ' ');

        return (
          <React.Fragment key={href}>
            <ChevronRight className="w-3 h-3 text-[#364036] shrink-0" />
            {isLast ? (
              <span className="text-[#F2F4EF] font-medium truncate max-w-[200px]" aria-current="page">
                {label}
              </span>
            ) : (
              <Link
                href={href}
                className="text-[#929B90] hover:text-[#F2F4EF] transition-colors truncate max-w-[150px]"
              >
                {label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
