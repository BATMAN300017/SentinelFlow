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
      {/* Toast Notification Container */}
      <aside
        aria-label="System notifications"
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((toast) => {
          const borderClass =
            toast.type === 'success'
              ? 'border-emerald-500/50 bg-emerald-950/90 text-emerald-200'
              : toast.type === 'error'
              ? 'border-rose-500/50 bg-rose-950/90 text-rose-200'
              : toast.type === 'warning'
              ? 'border-amber-500/50 bg-amber-950/90 text-amber-200'
              : 'border-sky-500/50 bg-sky-950/90 text-sky-200';

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
              className={`pointer-events-auto p-4 rounded-xl border shadow-2xl backdrop-blur-md flex items-start space-x-3 text-xs font-mono transition-all animate-fade-in ${borderClass}`}
            >
              <IconComponent className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                {toast.title && <div className="font-bold text-white mb-0.5">{toast.title}</div>}
                <div className="leading-relaxed break-words">{toast.message}</div>
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="shrink-0 p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition"
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
    // Graceful fallback if called outside provider
    return {
      showToast: () => {},
      dismissToast: () => {},
    };
  }
  return context;
}
