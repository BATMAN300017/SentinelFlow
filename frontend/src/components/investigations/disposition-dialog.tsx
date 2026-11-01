'use client';

import React, { useState } from 'react';
import { DispositionType, DispositionPayload } from '@/types/investigation';
import { X, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useToast } from '@/components/shared/toast';

interface DispositionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: DispositionPayload) => Promise<void>;
  caseNumber?: string;
}

export function DispositionDialog({
  isOpen,
  onClose,
  onSubmit,
  caseNumber = 'CASE-000',
}: DispositionDialogProps) {
  const { showToast } = useToast();
  const [disposition, setDisposition] = useState<DispositionType>('CONFIRMED_FRAUD');
  const [rationale, setRationale] = useState('');
  const [escalateSar, setEscalateSar] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rationale.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit({ disposition, rationale, escalate_sar: escalateSar });
      showToast({
        type: 'success',
        title: 'Disposition Submitted',
        message: `Case ${caseNumber} dispositioned as ${disposition.replace(/_/g, ' ')}.`,
      });
      onClose();
    } catch (err: any) {
      showToast({
        type: 'error',
        title: 'Submission Failed',
        message: err?.message || String(err) || 'Failed to submit case disposition.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in overflow-y-auto">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 max-h-[92vh] overflow-y-auto p-4 sm:p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-bold font-mono text-slate-100">
              Record Formal Disposition • {caseNumber}
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-mono font-semibold text-slate-300">
              Adjudication Outcome
            </label>
            <select
              value={disposition}
              onChange={(e) => setDisposition(e.target.value as DispositionType)}
              className="w-full px-3 py-2 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
            >
              <option value="CONFIRMED_FRAUD">Confirmed Fraud (High Risk Syndicate)</option>
              <option value="SUSPICIOUS_ACTIVITY_REPORT">Suspicious Activity Report (SAR Mandate)</option>
              <option value="FALSE_POSITIVE">False Positive (Benign Behavioral Deviation)</option>
              <option value="CLEARED">Cleared by Senior Investigator</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-mono font-semibold text-slate-300">
              Investigative Rationale & Evidence Grounding
            </label>
            <textarea
              rows={4}
              required
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="State verifiable account relationships, hop distances, and corroborating transaction IDs..."
              className="w-full p-3 rounded-xl text-xs font-mono bg-slate-950 text-slate-200 border border-slate-750 focus:outline-none focus:border-sky-500"
            />
          </div>

          <label className="flex items-center space-x-2 text-xs font-mono text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={escalateSar}
              onChange={(e) => setEscalateSar(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-sky-500 focus:ring-0"
            />
            <span>Escalate regulatory SAR filing to FIU Compliance Gateway</span>
          </label>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !rationale.trim()}
              className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition shadow-lg shadow-emerald-600/20"
            >
              {submitting ? 'Recording...' : 'Commit Disposition'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
