import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function resolveApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }

  // If in production build or running in non-localhost browser, default to production Render URL
  if (process.env.NODE_ENV === 'production') {
    return 'https://sentinelflow-ljlk.onrender.com/api/v1';
  }

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host !== 'localhost' && host !== '127.0.0.1') {
      return 'https://sentinelflow-ljlk.onrender.com/api/v1';
    }
  }

  return 'http://localhost:8000/api/v1';
}

export const API_BASE_URL = resolveApiBaseUrl();

export const RISK_BANDS = {
  ROUTINE: { label: 'Routine (0-24)', color: 'text-emerald-400 bg-emerald-950/60 border-emerald-800/80', dot: 'bg-emerald-500' },
  LOW: { label: 'Low (25-49)', color: 'text-sky-400 bg-sky-950/60 border-sky-800/80', dot: 'bg-sky-500' },
  ELEVATED: { label: 'Elevated (50-74)', color: 'text-amber-400 bg-amber-950/60 border-amber-800/80', dot: 'bg-amber-500' },
  HIGH: { label: 'High Priority (75-100)', color: 'text-rose-400 bg-rose-950/60 border-rose-800/80', dot: 'bg-rose-500' },
} as const;

export function getRiskBand(score: number): 'ROUTINE' | 'LOW' | 'ELEVATED' | 'HIGH' {
  if (score >= 75) return 'HIGH';
  if (score >= 50) return 'ELEVATED';
  if (score >= 25) return 'LOW';
  return 'ROUTINE';
}
