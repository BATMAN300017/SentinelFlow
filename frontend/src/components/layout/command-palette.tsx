'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, ArrowRight, X } from 'lucide-react';
import { NAVIGATION_SECTIONS } from '@/lib/constants';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Trigger handled in parent
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const allItems = NAVIGATION_SECTIONS.flatMap((s) => s.items);
  const filtered = query.trim()
    ? allItems.filter((i) =>
        i.name.toLowerCase().includes(query.toLowerCase()) ||
        i.href.toLowerCase().includes(query.toLowerCase())
      )
    : allItems;

  const handleSelect = (href: string) => {
    onClose();
    router.push(href);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#080A08]/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Palette Container */}
      <div className="relative w-full max-w-xl rounded bg-[#121612] border border-[#262D26] shadow-elevated overflow-hidden z-10 animate-fade-in">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-[#262D26]">
          <Search className="w-4 h-4 text-[#929B90] mr-3 shrink-0" />
          <input
            type="text"
            placeholder="Type a destination or search entity, transaction, rule..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="w-full bg-transparent text-sm font-mono text-[#F2F4EF] placeholder-[#687166] focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#181E18]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2">
          <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#687166]">
            Navigation Destinations
          </div>
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs font-mono text-[#687166]">
              No matching routes found
            </div>
          ) : (
            <div className="space-y-0.5">
              {filtered.map((item) => (
                <button
                  key={item.href}
                  onClick={() => handleSelect(item.href)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#181E18] group text-left transition"
                >
                  <span className="group-hover:text-[#F2F4EF]">{item.name}</span>
                  <div className="flex items-center space-x-2 text-[10px] text-[#687166]">
                    <span>{item.href}</span>
                    <ArrowRight className="w-3 h-3 group-hover:text-[#B7F34A] transition" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-[#262D26] bg-[#0D100D] flex items-center justify-between text-[10px] font-mono text-[#687166]">
          <span>Use arrows to navigate</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
}
