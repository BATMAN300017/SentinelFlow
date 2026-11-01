'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { ArrowLeft, Users, ShieldAlert, GitFork } from 'lucide-react';

export default function EntityDetailPageClient() {
  const params = useParams();
  const entityId = params?.id as string;
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!entityId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetchApi<any>(`/entities/${entityId}`);
        setProfile(res);
      } catch (e: any) {
        setError(e.message || `Failed to load profile for ${entityId}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [entityId]);

  useEffect(() => {
    document.title = entityId ? `Entity Profile (${entityId}) | SentinelFlow AI` : 'Entity Profile | SentinelFlow AI';
  }, [entityId]);

  return (
    <AppShell>
      <head>
        <title>{entityId ? `Entity Profile (${entityId}) | SentinelFlow AI` : 'Entity Profile | SentinelFlow AI'}</title>
        <meta name="description" content="In-depth entity counterparty risk profile, behavioral metrics, and connected financial crime alerts." />
      </head>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <Link
            href="/entities"
            className="flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Entity Profiles</span>
          </Link>
          {profile && (
            <span className="font-mono text-xs font-bold text-sky-400 bg-sky-950/80 px-2.5 py-1 rounded border border-sky-800">
              {profile.id}
            </span>
          )}
        </div>

        {loading ? (
          <LoadingState message="Loading entity risk profile..." rows={6} />
        ) : error || !profile ? (
          <ErrorState
            title="Entity Record Missing"
            message={error || `Entity ${entityId} could not be retrieved from the persistent graph store.`}
            onRetry={() => window.location.reload()}
          />
        ) : (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-sky-400">
                    {profile.entity_type || 'ACCOUNT'}
                  </span>
                  <h1 className="text-xl font-bold font-mono text-slate-100 mt-1">{profile.label || profile.id}</h1>
                </div>
                <StatusBadge type="severity" value={profile.risk_level || 'ROUTINE'} />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono pt-4 border-t border-slate-850">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Associated Alerts</span>
                  <div className="text-lg font-bold text-amber-400 mt-1">{profile.alert_count || 0}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Open Cases</span>
                  <div className="text-lg font-bold text-purple-400 mt-1">{profile.investigation_count || 0}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Risk Score</span>
                  <div className="text-lg font-bold text-rose-400 mt-1">{profile.risk_score || 24}/100</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-850">
                  <span className="text-slate-500 text-[10px]">Graph Role</span>
                  <div className="text-lg font-bold text-slate-200 mt-1">Intermediary</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
