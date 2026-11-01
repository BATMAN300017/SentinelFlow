'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { CheckCircle2, Send } from 'lucide-react';

export function OutcomeForm() {
  const [transactionId, setTransactionId] = useState('');
  const [analystDecision, setAnalystDecision] = useState('CONFIRMED_FRAUD');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transactionId.trim()) return;

    setSubmitting(true);
    setStatusMsg(null);

    try {
      await fetchApi('/learning/feedback', {
        method: 'POST',
        body: JSON.stringify({
          transaction_id: transactionId.trim(),
          analyst_decision: analystDecision,
          notes: notes.trim(),
        }),
      });

      setStatusMsg({
        text: 'Analyst outcome successfully committed to training store for next calibration cycle.',
        ok: true,
      });
      setTransactionId('');
      setNotes('');
    } catch (err: any) {
      setStatusMsg({
        text: err.message || 'Failed to record feedback.',
        ok: false,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center space-x-2">
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-100 font-mono">
          Ground-Truth Investigator Feedback Submission
        </h3>
      </div>
      <p className="text-xs text-slate-400 font-mono">
        Submit adjudicated transaction findings to update the persistent feedback loop and model training sets.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-mono font-semibold text-slate-300">
              Transaction ID
            </label>
            <input
              type="text"
              required
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              placeholder="e.g. TXN_0000602333"
              className="w-full px-3 py-2 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-mono font-semibold text-slate-300">
              Analyst Ground Truth Label
            </label>
            <select
              value={analystDecision}
              onChange={(e) => setAnalystDecision(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
            >
              <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD (Positive Label)</option>
              <option value="FALSE_POSITIVE">FALSE_POSITIVE (Negative Label)</option>
              <option value="SUSPICIOUS">SUSPICIOUS (Review Needed)</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-mono font-semibold text-slate-300">
            Adjudication Rationale
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Document evidentiary proof or rationale..."
            className="w-full p-3 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
          />
        </div>

        {statusMsg && (
          <div
            className={`p-3 rounded-xl text-xs font-mono border ${
              statusMsg.ok
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                : 'bg-rose-950/60 border-rose-800 text-rose-300'
            }`}
          >
            {statusMsg.text}
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={submitting || !transactionId.trim()}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white transition shadow-lg shadow-sky-600/20"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{submitting ? 'Submitting...' : 'Record Feedback'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
