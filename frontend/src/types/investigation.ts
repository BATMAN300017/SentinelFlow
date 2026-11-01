export type CasePriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type CaseStatus = 'NEW' | 'ASSIGNED' | 'IN_PROGRESS' | 'PENDING_REVIEW' | 'DISPOSITIONED' | 'CLOSED';
export type DispositionType = 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE' | 'SUSPICIOUS_ACTIVITY_REPORT' | 'CLEARED';

export interface InvestigationCase {
  id: string;
  case_number: string;
  title: string;
  summary: string;
  priority: CasePriority;
  status: CaseStatus;
  lead_analyst?: string;
  assigned_analyst?: string;
  disposition?: DispositionType;
  disposition_rationale?: string;
  evidence_completeness_score: number;
  created_at: string;
  updated_at: string;
  evidence_count?: number;
  accounts_involved?: string[];
  total_exposure_amount?: number;
}

export interface EvidenceItem {
  id: string;
  investigation_id: string;
  evidence_type: 'TRANSACTION' | 'IP_LOG' | 'DEVICE_FINGERPRINT' | 'GRAPH_CYCLE' | 'BENEFICIARY_CLUSTER';
  reference_id: string;
  description: string;
  confidence_score: number;
  metadata?: Record<string, any>;
  added_at: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  actor: string;
  category: 'DETECTION' | 'ACTION' | 'NOTE' | 'DISPOSITION';
}

export interface CaseNote {
  id: string;
  author: string;
  text: string;
  created_at: string;
}

export interface DispositionPayload {
  disposition: DispositionType;
  rationale: string;
  escalate_sar: boolean;
  block_accounts?: boolean;
}
