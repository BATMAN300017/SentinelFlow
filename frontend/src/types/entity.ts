export type EntityType = 'ACCOUNT' | 'CUSTOMER' | 'IP' | 'DEVICE' | 'BENEFICIARY';
export type RiskLevel = 'ROUTINE' | 'LOW' | 'ELEVATED' | 'HIGH' | 'CRITICAL';

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  risk_level: RiskLevel;
  properties?: {
    balance?: number;
    transaction_count?: number;
    flagged?: boolean;
    country?: string;
    account_type?: string;
    is_mule?: boolean;
    centrality?: number;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  amount: number;
  currency: string;
  transaction_count?: number;
  label?: string;
  timestamp?: string;
  is_flagged?: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  max_depth?: number;
  seed_account_id?: string;
  mule_chains_found?: number;
}

export interface EntityProfile {
  id: string;
  entity_type: EntityType;
  primary_identifier: string;
  risk_score: number;
  risk_level: RiskLevel;
  first_seen: string;
  last_seen: string;
  transaction_count: number;
  total_volume_in: number;
  total_volume_out: number;
  associated_alerts: number;
  tags: string[];
}
