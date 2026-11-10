'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  showToast: (toast: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(({ type, title, message, duration = 4000 }: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, title, message, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        dismissToast(id);
      }, duration);
    }
  }, [dismissToast]);

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}
      <aside
        aria-label="System notifications"
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((toast) => {
          const borderClass =
            toast.type === 'success'
              ? 'border-[#29421E] border-l-2 border-l-[#B7F34A] bg-[#142010] text-[#F2F4EF]'
              : toast.type === 'error'
              ? 'border-[#5A2020] border-l-2 border-l-[#FF4D4D] bg-[#2A1414] text-[#F2F4EF]'
              : toast.type === 'warning'
              ? 'border-[#5E4C1A] border-l-2 border-l-[#FFB800] bg-[#2A230F] text-[#F2F4EF]'
              : 'border-[#262D26] border-l-2 border-l-[#929B90] bg-[#181E18] text-[#F2F4EF]';

          const IconComponent =
            toast.type === 'success'
              ? CheckCircle2
              : toast.type === 'error'
              ? AlertCircle
              : toast.type === 'warning'
              ? AlertTriangle
              : Info;

          return (
            <div
              key={toast.id}
              role="alert"
              className={`pointer-events-auto p-3.5 rounded border shadow-elevated flex items-start space-x-3 text-xs font-mono transition-all animate-fade-in ${borderClass}`}
            >
              <IconComponent className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                {toast.title && <div className="font-bold text-[#F2F4EF] mb-0.5">{toast.title}</div>}
                <div className="leading-relaxed break-words text-[#929B90] text-[11px]">{toast.message}</div>
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="shrink-0 p-1 rounded hover:bg-[#262D26] text-[#687166] hover:text-[#F2F4EF] transition"
                aria-label="Dismiss notification"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </aside>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    // Graceful fallback during static page prerendering
    return {
      showToast: () => {},
      dismissToast: () => {},
    };
  }
  return context;
}
