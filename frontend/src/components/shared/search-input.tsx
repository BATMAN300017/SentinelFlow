'use client';

import React from 'react';
import { Search } from 'lucide-react';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Filter records...',
  className = '',
}: SearchInputProps) {
  return (
    <div className={`relative flex items-center ${className}`}>
      <Search className="w-3.5 h-3.5 text-[#687166] absolute left-3 pointer-events-none shrink-0" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-[#121612] text-xs font-mono text-[#F2F4EF] placeholder-[#687166] pl-8 pr-3 py-1.5 rounded border border-[#262D26] hover:border-[#364036] focus:border-[#B7F34A] focus:outline-none transition-colors"
      />
    </div>
  );
}
