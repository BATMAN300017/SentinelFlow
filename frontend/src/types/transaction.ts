export type RiskBand = 'ROUTINE' | 'LOW' | 'ELEVATED' | 'HIGH';

export interface Transaction {
  id: string;
  event_id: string;
  source_account_id: string;
  destination_account_id?: string;
  beneficiary_name?: string;
  customer_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  payment_channel: string;
  risk_score: number;
  risk_band?: RiskBand;
  status: string;
  created_at: string;
  anomaly_reasons?: string[];
  mule_indicators?: string[];
  ip_address?: string;
  location_country?: string;
}

export interface TransactionFilter {
  search?: string;
  risk_band?: string;
  channel?: string;
  min_score?: number;
  currency?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedTransactions {
  items: Transaction[];
  total?: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export interface RiskScoreBreakdown {
  rule_score: number;
  anomaly_score: number;
  graph_score: number;
  supervised_score: number;
  final_composite_score: number;
  contributing_factors: string[];
}
