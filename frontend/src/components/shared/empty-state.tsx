'use client';

import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({
  title = 'No Records Found',
  description = 'No surveillance items match the specified filter criteria.',
  action,
}: EmptyStateProps) {
  return (
    <div className="py-12 px-4 text-center rounded bg-[#121612] border border-[#262D26]">
      <div className="w-10 h-10 rounded bg-[#181E18] border border-[#262D26] text-[#687166] flex items-center justify-center mx-auto mb-3">
        <Inbox className="w-5 h-5" />
      </div>
      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F2F4EF]">{title}</h3>
      <p className="text-[11px] font-mono text-[#687166] mt-1 max-w-sm mx-auto">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
