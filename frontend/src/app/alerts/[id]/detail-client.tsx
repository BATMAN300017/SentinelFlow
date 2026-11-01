'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function AlertDetailPageClient() {
  const params = useParams();
  const alertId = params?.id as string;
  const [alertData, setAlertData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlert() {
      if (!alertId) return;
      try {
        const res = await fetchApi<any>(`/alerts/${alertId}`);
        setAlertData(res);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadAlert();
  }, [alertId]);

  if (loading) return <div className="p-8 text-center text-slate-400">Loading alert details...</div>;
  if (!alertData) return <div className="p-8 text-center text-slate-400">Alert not found.</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/alerts" className="text-xs text-slate-500 hover:text-slate-800">&larr; Back to Alerts</Link>
        <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded border border-sky-200">{alertData.alert_ref}</span>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h1 className="text-xl font-bold text-slate-900">{alertData.title}</h1>
        <p className="text-xs text-slate-600">{alertData.summary}</p>
        <div className="grid grid-cols-2 gap-4 text-xs pt-4 border-t border-slate-100">
          <div><span className="font-semibold text-slate-700">Account ID:</span> {alertData.account_id}</div>
          <div><span className="font-semibold text-slate-700">Severity:</span> {alertData.severity}</div>
          <div><span className="font-semibold text-slate-700">Risk Score:</span> {alertData.risk_score} / 100</div>
          <div><span className="font-semibold text-slate-700">Status:</span> {alertData.status}</div>
        </div>
      </div>
    </div>
  );
}
