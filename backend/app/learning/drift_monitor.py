import sqlite3
from typing import Dict, Any

def check_label_and_prediction_drift(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    
    # 1. Check positive feedback ratio over time (Excluding demo fixtures)
    cursor.execute("""
        SELECT training_label, COUNT(*)
        FROM analyst_feedback
        WHERE is_eligible_for_training = 1
          AND (exclusion_reason IS NULL OR exclusion_reason != 'DEMO_FIXTURE')
        GROUP BY training_label
    """)
    rows = cursor.fetchall()
    counts = {r[0]: r[1] for r in rows}
    
    pos = counts.get(1, 0)
    neg = counts.get(0, 0)
    total = pos + neg
    
    pos_rate = round(pos / total, 3) if total > 0 else 0.0
    
    # 2. Check risk score drift across last 200 transactions (Excluding demo fixtures)
    cursor.execute("""
        SELECT AVG(risk_score)
        FROM (
            SELECT risk_score FROM transactions 
            WHERE (dataset_source IS NULL OR dataset_source != 'DEMO_FIXTURE')
            ORDER BY created_at DESC LIMIT 200
        )
    """)
    avg_score_row = cursor.fetchone()
    recent_avg_score = round(float(avg_score_row[0] or 0.0), 2)
    
    drift_warning = False
    warning_reason = None
    if total >= 20 and (pos_rate > 0.85 or pos_rate < 0.15):
        drift_warning = True
        warning_reason = f"Label distribution shift detected: {pos_rate*100:.1f}% positive label prevalence"
        
    return {
        "total_eligible_samples": total,
        "positive_labels": pos,
        "negative_labels": neg,
        "positive_rate": pos_rate,
        "recent_transaction_avg_risk": recent_avg_score,
        "drift_warning": drift_warning,
        "warning_reason": warning_reason
    }
