'use client';

import React from 'react';
import { SearchInput } from './search-input';
import { RotateCcw } from 'lucide-react';

interface FilterOption {
  label: string;
  value: string;
}

interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;
  options?: {
    name: string;
    value: string;
    items: FilterOption[];
    onChange: (val: string) => void;
  }[];
  onReset?: () => void;
}

export function FilterBar({
  searchValue = '',
  onSearchChange,
  searchPlaceholder = 'Filter records...',
  options = [],
  onReset,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
      <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
        {onSearchChange && (
          <div className="w-full sm:w-72">
            <SearchInput value={searchValue} onChange={onSearchChange} placeholder={searchPlaceholder} />
          </div>
        )}

        {options.map((opt) => (
          <select
            key={opt.name}
            value={opt.value}
            onChange={(e) => opt.onChange(e.target.value)}
            className="px-3 py-1.5 rounded-lg text-xs font-mono bg-slate-800 text-slate-200 border border-slate-700 focus:outline-none focus:border-sky-500"
          >
            {opt.items.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        ))}
      </div>

      {onReset && (
        <button
          onClick={onReset}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      )}
    </div>
  );
}
