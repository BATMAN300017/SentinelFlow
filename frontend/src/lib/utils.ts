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
  CRITICAL: { label: 'Critical Risk', color: 'text-rose-400 bg-rose-950/40 border-rose-500/30', dot: 'bg-rose-500', tier: 'CRITICAL' },
  HIGH: { label: 'High Risk', color: 'text-orange-400 bg-orange-950/40 border-orange-500/30', dot: 'bg-orange-500', tier: 'HIGH' },
  MEDIUM: { label: 'Medium Risk', color: 'text-amber-400 bg-amber-950/40 border-amber-500/30', dot: 'bg-amber-500', tier: 'MEDIUM' },
  ELEVATED: { label: 'Medium Risk', color: 'text-amber-400 bg-amber-950/40 border-amber-500/30', dot: 'bg-amber-500', tier: 'MEDIUM' },
  LOW: { label: 'Low Risk', color: 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30', dot: 'bg-emerald-500', tier: 'LOW' },
  NEUTRAL: { label: 'Neutral', color: 'text-slate-400 bg-slate-900/60 border-slate-700/40', dot: 'bg-slate-500', tier: 'NEUTRAL' },
  ROUTINE: { label: 'Neutral', color: 'text-slate-400 bg-slate-900/60 border-slate-700/40', dot: 'bg-slate-500', tier: 'NEUTRAL' },
} as const;

export function getRiskBand(score: number): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NEUTRAL' {
  if (score >= 85) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 45) return 'MEDIUM';
  if (score >= 15) return 'LOW';
  return 'NEUTRAL';
}
