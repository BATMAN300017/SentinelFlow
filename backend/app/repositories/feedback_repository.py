import sqlite3
from typing import Dict, Any, List, Optional
from app.utils.ids import generate_id
from app.utils.time import utc_now_iso

def record_feedback(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    f_id = generate_id("FDB")
    now = utc_now_iso()
    cursor = conn.cursor()
    inv_id = data.get("investigation_id")

    alert_id = None
    txn_id = None
    account_id = None
    if inv_id:
        try:
            cursor.execute("""
                SELECT a.id, a.transaction_id, a.account_id
                FROM investigation_alerts ia
                JOIN alerts a ON ia.alert_id = a.id
                WHERE ia.investigation_id = ? LIMIT 1
            """, (inv_id,))
            a_row = cursor.fetchone()
            if a_row:
                alert_id = a_row[0] if not hasattr(a_row, "keys") else a_row["id"]
                txn_id = a_row[1] if not hasattr(a_row, "keys") else a_row["transaction_id"]
                account_id = a_row[2] if not hasattr(a_row, "keys") else a_row["account_id"]
        except Exception:
            pass

    # Insert into investigator_feedback
    try:
        cursor.execute("""
            INSERT INTO investigator_feedback (
                id, alert_id, transaction_id, account_id, investigation_id,
                investigator_decision, explanation, supporting_evidence,
                reviewer_id, reviewer_name, model_version, is_eligible_for_training,
                training_label, exclusion_reason, validation_status, created_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, 'Investigator', ?, ?,
                ?, ?, 'PENDING_VALIDATION', ?
            ) ON CONFLICT (id) DO NOTHING;
        """, (
            f_id, alert_id, txn_id, account_id, inv_id,
            data["disposition"], data.get("rationale", ""), "Investigation Case Review",
            data.get("analyst_id", "USR-INV-01"), data.get("model_version", "v1.0.0"),
            data.get("is_eligible_for_training", 0), data.get("training_label"),
            data.get("exclusion_reason"), now
        ))
    except Exception:
        pass

    cursor.execute("""
        INSERT INTO analyst_feedback (
            id, investigation_id, transaction_id, analyst_id, disposition, analyst_decision, rationale,
            evidence_reviewed_count, is_eligible_for_training, training_label,
            exclusion_reason, model_version, rule_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING;
    """, (
        f_id, inv_id, txn_id, data["analyst_id"], data["disposition"], data["disposition"],
        data["rationale"], data.get("evidence_reviewed_count", 0),
        data["is_eligible_for_training"], data.get("training_label"),
        data.get("exclusion_reason"), data.get("model_version", "v1.0"),
        data.get("rule_version", "v1.0"), now
    ))
    return {**data, "id": f_id, "created_at": now}

def get_feedback_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'CONFIRMED_FRAUD'")
    fraud_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition IN ('LEGITIMATE_ACTIVITY', 'FALSE_POSITIVE')")
    fp_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'INCONCLUSIVE'")
    inconclusive_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'SUSPICIOUS_UNCONFIRMED'")
    suspicious_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE is_eligible_for_training = 1")
    eligible_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE training_label = 1")
    pos_lbls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE training_label = 0")
    neg_lbls = cursor.fetchone()[0]
    
    cursor.execute("SELECT created_at FROM analyst_feedback ORDER BY created_at DESC LIMIT 1")
    last_row = cursor.fetchone()
    last_fb = last_row[0] if last_row else None
    
    return {
        "total_feedback_count": total,
        "confirmed_fraud_count": fraud_cnt,
        "false_positive_count": fp_cnt,
        "inconclusive_count": inconclusive_cnt,
        "suspicious_unconfirmed_count": suspicious_cnt,
        "eligible_for_training_count": eligible_cnt,
        "positive_labels": pos_lbls,
        "negative_labels": neg_lbls,
        "last_feedback_at": last_fb
    }
