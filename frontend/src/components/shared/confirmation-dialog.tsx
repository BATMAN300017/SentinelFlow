'use client';

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Cancel',
  isDestructive = false,
}: ConfirmationDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in overflow-y-auto">
      <div className="w-full max-w-md max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-4 sm:p-6 shadow-2xl space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2 rounded-xl ${
                isDestructive ? 'bg-rose-950/80 text-rose-400 border border-rose-800' : 'bg-sky-950/80 text-sky-400 border border-sky-800'
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100 font-mono">{title}</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-400 font-mono leading-relaxed">{description}</p>

        <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-mono font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            {cancelLabel}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition shadow-lg ${
              isDestructive
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/30'
                : 'bg-sky-600 hover:bg-sky-500 text-white shadow-sky-900/30'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
