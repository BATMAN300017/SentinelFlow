import { Transaction } from '@/types/transaction';
import { InvestigationCase } from '@/types/investigation';

export function isNonEmptyString(val: any): val is string {
  return typeof val === 'string' && val.trim().length > 0;
}

export function isValidTransaction(tx: any): tx is Transaction {
  return (
    typeof tx === 'object' &&
    tx !== null &&
    typeof tx.id === 'string' &&
    typeof tx.amount === 'number'
  );
}

export function isValidCase(c: any): c is InvestigationCase {
  return (
    typeof c === 'object' &&
    c !== null &&
    typeof c.id === 'string' &&
    typeof c.case_number === 'string'
  );
}

export function sanitizeRiskScore(score: any): number {
  const num = Number(score);
  if (isNaN(num)) return 0;
  return Math.max(0, Math.min(100, Math.round(num)));
}
