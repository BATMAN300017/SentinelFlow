'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/app-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { AlertExplanation } from '@/components/alerts/alert-explanation';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { ArrowLeft, ShieldAlert } from 'lucide-react';

export default function AlertDetailPageClient() {
  const params = useParams();
  const alertId = params?.id as string;
  const [alertData, setAlertData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAlert() {
      if (!alertId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetchApi<any>(`/alerts/${alertId}`);
        setAlertData(res);
      } catch (e: any) {
        setError(e.message || `Failed to load alert ${alertId}`);
      } finally {
        setLoading(false);
      }
    }
    loadAlert();
  }, [alertId]);

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <Link
            href="/alerts"
            className="flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Alerts Queue</span>
          </Link>
          {alertData && (
            <span className="font-mono text-xs font-bold text-sky-400 bg-sky-950/80 px-2.5 py-1 rounded border border-sky-800">
              {alertData.alert_ref}
            </span>
          )}
        </div>

        {loading ? (
          <LoadingState message="Loading alert details..." rows={6} />
        ) : error || !alertData ? (
          <ErrorState
            title="Alert Not Found"
            message={error || `Alert ID ${alertId} could not be retrieved from the database.`}
            onRetry={() => window.location.reload()}
          />
        ) : (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <StatusBadge type="severity" value={alertData.severity} />
                    <StatusBadge type="case_status" value={alertData.status} />
                  </div>
                  <h1 className="text-xl font-bold font-mono text-slate-100 mt-1">{alertData.title}</h1>
                </div>
                <StatusBadge type="risk" value={alertData.risk_score} />
              </div>

              <p className="text-xs text-slate-400 font-mono leading-relaxed">{alertData.summary}</p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono pt-4 border-t border-slate-850">
                <div>
                  <span className="text-slate-500">Account ID:</span>{' '}
                  <span className="text-slate-200 font-bold">{alertData.account_id}</span>
                </div>
                <div>
                  <span className="text-slate-500">Transaction ID:</span>{' '}
                  <span className="text-slate-200 font-bold">{alertData.transaction_id}</span>
                </div>
                <div>
                  <span className="text-slate-500">Risk Score:</span>{' '}
                  <span className="text-rose-400 font-bold">{alertData.risk_score} / 100</span>
                </div>
                <div>
                  <span className="text-slate-500">Detected:</span>{' '}
                  <span className="text-slate-300">
                    {new Date(alertData.created_at || Date.now()).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <AlertExplanation alert={alertData} />
          </div>
        )}
      </div>
    </AppShell>
  );
}
