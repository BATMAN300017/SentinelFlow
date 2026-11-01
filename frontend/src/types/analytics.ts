export interface DashboardSummary {
  transactions_processed: number;
  transactions_per_minute: number;
  alerts_generated: number;
  open_investigations: number;
  high_priority_alerts?: number;
  confirmed_fraud_count?: number;
  prevented_loss_amount?: number;
  system_health?: string;
}

export interface RiskDistributionBand {
  band: string;
  count: number;
  percentage?: number;
}

export interface DashboardTrends {
  risk_score_distribution: RiskDistributionBand[];
  throughput_series?: { timestamp: string; count: number }[];
  alert_timeline?: { date: string; low: number; medium: number; high: number }[];
}

export interface ModelMetricSet {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  brier_score?: number;
  evaluated_samples: number;
  evaluation_date?: string;
}

export interface ModelEvaluation {
  model_name: string;
  version: string;
  status: 'ACTIVE' | 'EVALUATED' | 'TRAINING' | 'CANDIDATE';
  evaluation_granularity: string;
  metrics: ModelMetricSet;
  features_used?: string[];
  training_dataset?: string;
  last_retrained_at?: string;
}

export interface DatasetRecord {
  id: string;
  title: string;
  version: string;
  domain: string;
  transaction_count: number;
  confirmed_fraud_count: number;
  provenance_source: string;
  created_at: string;
}
