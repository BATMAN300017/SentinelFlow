'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { useRouter } from 'next/navigation';
import { Shield, Lock, User, ArrowRight } from 'lucide-react';
import { APP_NAME, APP_TAGLINE } from '@/lib/constants';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('sarah_investigator');
  const [password, setPassword] = useState('password123');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetchApi<any>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem('sentinel_token', res.access_token);
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4 font-mono">
      <div className="w-full max-w-md p-8 rounded-3xl border border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-xl space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-white mx-auto shadow-lg shadow-sky-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">{APP_NAME}</h1>
          <p className="text-xs text-slate-400">{APP_TAGLINE}</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-slate-300 font-medium">Username / Operator Handle</label>
            <div className="relative flex items-center">
              <User className="absolute left-3 w-4 h-4 text-slate-500 pointer-events-none" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-950 text-slate-100 border border-slate-750 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-300 font-medium">Password</label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 w-4 h-4 text-slate-500 pointer-events-none" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-950 text-slate-100 border border-slate-750 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-xl font-bold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white transition flex items-center justify-center space-x-2 shadow-lg shadow-sky-600/20"
          >
            <span>{submitting ? 'Authenticating...' : 'Sign In to Command Center'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-500 text-center">
          Production Security Perimeter • Render Backend Gateway
        </div>
      </div>
    </div>
  );
}
