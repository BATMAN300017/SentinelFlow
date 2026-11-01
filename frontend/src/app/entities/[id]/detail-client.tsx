'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function EntityDetailPageClient() {
  const params = useParams();
  const entityId = params?.id as string;
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      if (!entityId) return;
      try {
        const res = await fetchApi<any>(`/entities/${entityId}`);
        setProfile(res);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, [entityId]);

  if (!profile) return <div className="p-8 text-center text-slate-400">Loading entity profile...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <Link href="/entities" className="text-xs text-slate-500 hover:text-slate-800">&larr; Back to Entities</Link>
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <h1 className="text-xl font-bold text-slate-900">{profile.label}</h1>
        <p className="text-xs text-slate-500 font-mono">Entity Type: {profile.entity_type} | ID: {profile.id}</p>
        <div className="pt-3 border-t border-slate-100 text-xs space-y-1">
          <div><b>Alert Count:</b> {profile.alert_count}</div>
          <div><b>Investigation Count:</b> {profile.investigation_count}</div>
        </div>
      </div>
    </div>
  );
}
