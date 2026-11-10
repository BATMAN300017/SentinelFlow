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

// Institutional Risk Bands: Disciplined risk coloring, no green for fraud
export const RISK_BANDS = {
  CRITICAL: {
    label: 'Critical Risk',
    color: 'text-[#FF6B6B] bg-[#2A1414] border-[#5A2020]',
    dot: 'bg-[#FF4D4D]',
    tier: 'CRITICAL',
  },
  HIGH: {
    label: 'High Risk',
    color: 'text-[#FFA14A] bg-[#2E1A0F] border-[#663518]',
    dot: 'bg-[#FF8833]',
    tier: 'HIGH',
  },
  MEDIUM: {
    label: 'Medium Risk',
    color: 'text-[#FFD15C] bg-[#2A230F] border-[#5E4C1A]',
    dot: 'bg-[#FFB800]',
    tier: 'MEDIUM',
  },
  ELEVATED: {
    label: 'Elevated Risk',
    color: 'text-[#FFD15C] bg-[#2A230F] border-[#5E4C1A]',
    dot: 'bg-[#FFB800]',
    tier: 'MEDIUM',
  },
  LOW: {
    label: 'Low Risk',
    color: 'text-[#B7F34A] bg-[#142010] border-[#29421E]',
    dot: 'bg-[#B7F34A]',
    tier: 'LOW',
  },
  NEUTRAL: {
    label: 'Routine',
    color: 'text-[#929B90] bg-[#121612] border-[#262D26]',
    dot: 'bg-[#687166]',
    tier: 'NEUTRAL',
  },
  ROUTINE: {
    label: 'Routine',
    color: 'text-[#929B90] bg-[#121612] border-[#262D26]',
    dot: 'bg-[#687166]',
    tier: 'NEUTRAL',
  },
} as const;

export function getRiskBand(score: number): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NEUTRAL' {
  if (score >= 85) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 45) return 'MEDIUM';
  if (score >= 15) return 'LOW';
  return 'NEUTRAL';
}
