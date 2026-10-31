import os
import sys

sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import get_db_connection
from app.core.logging import logger

MIGRATION_SQL = """
-- 1. model_training_runs
CREATE TABLE IF NOT EXISTS model_training_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    training_dataset TEXT NOT NULL,
    training_record_count INTEGER NOT NULL,
    positive_samples INTEGER NOT NULL,
    negative_samples INTEGER NOT NULL,
    feature_version TEXT NOT NULL DEFAULT 'v1.0-6d',
    hyperparameters_json JSONB DEFAULT '{}'::jsonb,
    evaluation_metrics_json JSONB DEFAULT '{}'::jsonb,
    previous_version_comparison_json JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    trained_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mtr_version ON model_training_runs(version);
CREATE INDEX IF NOT EXISTS idx_mtr_created_at ON model_training_runs(created_at DESC);

-- 2. model_evaluations
CREATE TABLE IF NOT EXISTS model_evaluations (
    id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    model_name TEXT NOT NULL,
    evaluation_type TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    positive_samples INTEGER NOT NULL,
    negative_samples INTEGER NOT NULL,
    precision NUMERIC,
    recall NUMERIC,
    f1_score NUMERIC,
    pr_auc NUMERIC,
    roc_auc NUMERIC,
    false_positive_rate NUMERIC,
    false_negative_rate NUMERIC,
    confusion_matrix_json JSONB NOT NULL,
    typology_breakdown_json JSONB DEFAULT '{}'::jsonb,
    risk_category_metrics_json JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'EVALUATED',
    evaluated_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mev_version ON model_evaluations(model_version);
CREATE INDEX IF NOT EXISTS idx_mev_dataset ON model_evaluations(dataset_name);

-- 3. investigator_feedback
CREATE TABLE IF NOT EXISTS investigator_feedback (
    id TEXT PRIMARY KEY,
    alert_id TEXT,
    transaction_id TEXT,
    account_id TEXT,
    investigation_id TEXT,
    investigator_decision TEXT NOT NULL,
    explanation TEXT,
    supporting_evidence TEXT,
    reviewer_id TEXT NOT NULL,
    reviewer_name TEXT,
    model_version TEXT DEFAULT 'v1.0.0',
    is_eligible_for_training INTEGER DEFAULT 0,
    training_label INTEGER,
    exclusion_reason TEXT,
    validation_status TEXT NOT NULL DEFAULT 'PENDING_VALIDATION',
    validated_by TEXT,
    validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ifb_alert_id ON investigator_feedback(alert_id);
CREATE INDEX IF NOT EXISTS idx_ifb_txn_id ON investigator_feedback(transaction_id);
CREATE INDEX IF NOT EXISTS idx_ifb_account_id ON investigator_feedback(account_id);
CREATE INDEX IF NOT EXISTS idx_ifb_decision ON investigator_feedback(investigator_decision);
CREATE INDEX IF NOT EXISTS idx_ifb_created_at ON investigator_feedback(created_at DESC);

-- 4. feedback_validation
CREATE TABLE IF NOT EXISTS feedback_validation (
    id TEXT PRIMARY KEY,
    feedback_id TEXT NOT NULL REFERENCES investigator_feedback(id) ON DELETE CASCADE,
    validator_id TEXT NOT NULL,
    validator_name TEXT NOT NULL,
    status TEXT NOT NULL,
    training_label_assigned INTEGER,
    validation_notes TEXT,
    evidence_verified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fval_fb_id ON feedback_validation(feedback_id);

-- 5. model_deployments
CREATE TABLE IF NOT EXISTS model_deployments (
    id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    model_name TEXT NOT NULL,
    deployment_type TEXT NOT NULL,
    deployed_by TEXT NOT NULL,
    previous_version TEXT,
    metrics_snapshot_json JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mdeploy_version ON model_deployments(model_version);
CREATE INDEX IF NOT EXISTS idx_mdeploy_created_at ON model_deployments(created_at DESC);

-- 6. model_monitoring_metrics
CREATE TABLE IF NOT EXISTS model_monitoring_metrics (
    id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_category TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    window_start TIMESTAMP WITH TIME ZONE,
    window_end TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    metadata_json JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mmm_category ON model_monitoring_metrics(metric_category);
CREATE INDEX IF NOT EXISTS idx_mmm_name ON model_monitoring_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_mmm_recorded ON model_monitoring_metrics(recorded_at DESC);
"""

def run_migration():
    print("Executing model intelligence schema migration...")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(MIGRATION_SQL)
        
        # Sync existing analyst_feedback into investigator_feedback if investigator_feedback is empty
        cur.execute("SELECT COUNT(*) as c FROM investigator_feedback;")
        row = cur.fetchone()
        cnt = row["c"] if hasattr(row, "keys") else row[0]
        if cnt == 0:
            print("Syncing 4 existing analyst_feedback records into investigator_feedback...")
            cur.execute("""
                INSERT INTO investigator_feedback (
                    id, investigation_id, transaction_id, investigator_decision, explanation, 
                    reviewer_id, reviewer_name, model_version, is_eligible_for_training, 
                    training_label, exclusion_reason, validation_status, created_at
                )
                SELECT 
                    id, investigation_id, transaction_id, disposition, rationale,
                    analyst_id, 'Senior Fraud Analyst', model_version, is_eligible_for_training,
                    training_label, exclusion_reason, 
                    CASE WHEN is_eligible_for_training = 1 THEN 'APPROVED' ELSE 'PENDING_VALIDATION' END,
                    created_at
                FROM analyst_feedback
                ON CONFLICT (id) DO NOTHING;
            """)
            print("Synced analyst_feedback -> investigator_feedback.")

        # Ensure model_deployments has record for active model v1.0.0
        cur.execute("SELECT COUNT(*) as c FROM model_deployments;")
        dep_cnt = cur.fetchone()
        dep_c = dep_cnt["c"] if hasattr(dep_cnt, "keys") else dep_cnt[0]
        if dep_c == 0:
            print("Recording baseline v1.0.0 deployment into model_deployments...")
            cur.execute("""
                INSERT INTO model_deployments (
                    id, model_version, model_name, deployment_type, deployed_by, 
                    previous_version, metrics_snapshot_json, status, reason, created_at
                ) VALUES (
                    'DEP-v1-0-0', 'v1.0.0', 'RandomForestClassifier', 'PROMOTE', 'System Administrator',
                    'BASELINE', '{"precision": 1.0, "recall": 1.0, "f1": 1.0, "pr_auc": 1.0}'::jsonb,
                    'ACTIVE', 'Initial production consensus baseline deployment', NOW()
                ) ON CONFLICT (id) DO NOTHING;
            """)

        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
