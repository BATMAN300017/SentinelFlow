'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const path = window.location.pathname;
    const search = window.location.search;

    if (!path || path === '/' || path === '/index.html' || path === '/200.html') {
      router.replace('/dashboard');
      return;
    }

    // Check if the user navigated directly or refreshed on a dynamic parameterized route
    const txnMatch = path.match(/^\/transactions\/([^/]+)/);
    if (txnMatch && txnMatch[1] && txnMatch[1] !== 'sample') {
      router.replace(`/transactions?id=${encodeURIComponent(txnMatch[1])}`);
      return;
    }

    const invMatch = path.match(/^\/investigations\/([^/]+)/);
    if (invMatch && invMatch[1] && invMatch[1] !== 'sample') {
      router.replace(`/investigations?id=${encodeURIComponent(invMatch[1])}`);
      return;
    }

    const alertMatch = path.match(/^\/alerts\/([^/]+)/);
    if (alertMatch && alertMatch[1] && alertMatch[1] !== 'sample') {
      router.replace(`/alerts?id=${encodeURIComponent(alertMatch[1])}`);
      return;
    }

    // Otherwise, preserve the target path
    router.replace(path + search);
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center font-mono text-xs text-slate-500">
      <div className="flex items-center space-x-3">
        <div className="w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span>Routing to SentinelFlow Workspace...</span>
      </div>
    </div>
  );
}
