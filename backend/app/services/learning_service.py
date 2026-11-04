import sqlite3
from typing import Dict, Any
from app.learning.dataset_builder import build_training_dataset
from app.learning.trainer import train_candidate_model
from app.learning.drift_monitor import check_label_and_prediction_drift
from app.learning.model_registry import get_registry_status, register_candidate, promote_candidate, rollback_model
from app.services.audit_service import record_audit_event

def get_complete_learning_status(conn: sqlite3.Connection) -> Dict[str, Any]:
    registry = get_registry_status()
    drift = check_label_and_prediction_drift(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM analyst_feedback 
        WHERE is_eligible_for_training = 1
          AND (exclusion_reason IS NULL OR exclusion_reason != 'DEMO_FIXTURE')
    """)
    eligible_count = cursor.fetchone()[0]
    
    readiness = "INSUFFICIENT"
    if eligible_count >= 20:
        readiness = "READY"
        if eligible_count >= 100:
            readiness = "CRITICAL_MASS"
            
    return {
        "current_active_model": registry["active_version"],
        "active_model_metrics": registry["active_metrics"],
        "candidate_model_available": registry["candidate_available"],
        "candidate_model_metrics": registry["candidate_metrics"],
        "training_data_readiness": readiness,
        "labeled_samples_count": eligible_count,
        "minimum_required_samples": 20,
        "drift_warning": drift["drift_warning"],
        "drift_details": drift,
        "last_evaluation_status": "PASSED" if registry["candidate_available"] else None
    }

def execute_candidate_training(conn: sqlite3.Connection, actor_name: str) -> Dict[str, Any]:
    dataset = build_training_dataset(conn)
    train_result = train_candidate_model(dataset)
    
    if train_result["success"]:
        cand_ver = train_result["candidate_version"]
        eval_report = train_result["eval_report"]
        if eval_report["passed"]:
            register_candidate(cand_ver, train_result["model"], eval_report["metrics"])
            record_audit_event(
                conn, None, actor_name, "TRAIN_CANDIDATE_MODEL", "MODEL", cand_ver,
                {"metrics": eval_report["metrics"], "status": "REGISTERED_CANDIDATE"}
            )
        else:
            record_audit_event(
                conn, None, actor_name, "TRAIN_CANDIDATE_MODEL", "MODEL", cand_ver,
                {"status": "FAILED_EVALUATION", "reason": eval_report["reason"]}
            )
            
    return train_result

def execute_model_promotion(conn: sqlite3.Connection, actor_name: str) -> Dict[str, Any]:
    res = promote_candidate(conn, actor_name)
    if res["success"]:
        record_audit_event(conn, None, actor_name, "PROMOTE_MODEL", "MODEL", res["new_version"], res)
    return res

def execute_model_rollback(conn: sqlite3.Connection, actor_name: str) -> Dict[str, Any]:
    res = rollback_model(conn, actor_name)
    record_audit_event(conn, None, actor_name, "ROLLBACK_MODEL", "MODEL", "LOGREG_V1_BASELINE", res)
    return res
