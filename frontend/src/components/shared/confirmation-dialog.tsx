'use client';

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Cancel',
  destructive = false,
}: ConfirmationDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#080A08]/85 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Dialog Box */}
      <div className="relative w-full max-w-md rounded bg-[#121612] border border-[#262D26] shadow-elevated p-6 z-10 animate-fade-in font-mono">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded ${destructive ? 'bg-[#2A1414] text-[#FF4D4D] border border-[#5A2020]' : 'bg-[#181E18] text-[#B7F34A] border border-[#262D26]'}`}>
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-[#F2F4EF]">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#687166] hover:text-[#F2F4EF] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="mt-4 text-xs text-[#929B90] leading-relaxed">{message}</p>

        <div className="mt-6 flex items-center justify-end space-x-3 text-xs">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#181E18] text-[#929B90] hover:text-[#F2F4EF] hover:bg-[#1F261F] border border-[#262D26] transition"
          >
            {cancelLabel}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-3 py-1.5 rounded font-semibold transition ${
              destructive
                ? 'bg-[#2A1414] text-[#FF6B6B] hover:bg-[#3D1A1A] border border-[#5A2020]'
                : 'bg-[#B7F34A] text-[#080A08] hover:bg-[#C9FF65]'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
