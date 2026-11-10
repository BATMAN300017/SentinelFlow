import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

def get_kpi_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    # 1. Transaction count: fast count minus demo fixtures without unindexed scan
    try:
        cursor.execute("SELECT COUNT(*) FROM transactions")
        row_tx = cursor.fetchone()
        total_txns = int((row_tx[0] if not hasattr(row_tx, "keys") else row_tx["count"]) or 0)
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE dataset_source = 'DEMO_FIXTURE'")
        row_demo = cursor.fetchone()
        demo_txns = int((row_demo[0] if not hasattr(row_demo, "keys") else row_demo["count"]) or 0)
        txns_count = max(0, total_txns - demo_txns)
    except Exception:
        txns_count = 0
    
    # 2. Alerts count: direct count without heavy subquery across transaction table
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE (is_demo IS NULL OR is_demo = 0)
              AND id NOT LIKE 'ALT-DEMO%'
              AND title NOT LIKE '[DEMO FIXTURE]%'
        """)
        row_al = cursor.fetchone()
        alerts_count = int((row_al[0] if not hasattr(row_al, "keys") else row_al["count"]) or 0)
    except Exception:
        alerts_count = 0
    
    # 3. Investigations metrics: unified single query with conditional aggregation
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_invs,
                COUNT(CASE WHEN status != 'RESOLVED' THEN 1 END) as open_invs,
                COUNT(CASE WHEN priority = 'HIGH' AND status != 'RESOLVED' THEN 1 END) as high_priority,
                COUNT(CASE WHEN disposition = 'CONFIRMED_FRAUD' THEN 1 END) as confirmed_fraud,
                COUNT(CASE WHEN disposition IN ('LEGITIMATE_ACTIVITY', 'FALSE_POSITIVE') THEN 1 END) as fps,
                COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved
            FROM investigations 
            WHERE (is_demo IS NULL OR is_demo = 0)
              AND id NOT LIKE 'INV-DEMO%'
              AND case_number NOT LIKE 'CASE-DEMO%'
              AND title NOT LIKE '[DEMO FIXTURE]%'
        """)
        inv_row = cursor.fetchone()
        total_invs = int((inv_row["total_invs"] if hasattr(inv_row, "keys") else inv_row[0]) or 0)
        open_invs = int((inv_row["open_invs"] if hasattr(inv_row, "keys") else inv_row[1]) or 0)
        high_priority = int((inv_row["high_priority"] if hasattr(inv_row, "keys") else inv_row[2]) or 0)
        confirmed_fraud = int((inv_row["confirmed_fraud"] if hasattr(inv_row, "keys") else inv_row[3]) or 0)
        fps = int((inv_row["fps"] if hasattr(inv_row, "keys") else inv_row[4]) or 0)
        resolved = int((inv_row["resolved"] if hasattr(inv_row, "keys") else inv_row[5]) or 0)
    except Exception:
        total_invs = open_invs = high_priority = confirmed_fraud = fps = resolved = 0
    
    completion_rate = round((resolved / total_invs) * 100.0, 1) if total_invs > 0 else 0.0
    total_reviewed = confirmed_fraud + fps
    fpr = round((fps / total_reviewed) * 100.0, 1) if total_reviewed > 0 else 0.0
    
    # 4. Total accounts: dynamic query, never hardcoded
    total_accounts = None
    try:
        cursor.execute("SELECT COUNT(*) FROM accounts")
        row_acc = cursor.fetchone()
        if row_acc:
            total_accounts = int(row_acc[0] if not hasattr(row_acc, "keys") else row_acc["count"])
    except Exception:
        total_accounts = None

    # 5. Dynamic average investigation age (hours) from open cases
    avg_inv_age = None
    try:
        cursor.execute("""
            SELECT created_at FROM investigations 
            WHERE status != 'RESOLVED' 
              AND (is_demo IS NULL OR is_demo = 0)
              AND id NOT LIKE 'INV-DEMO%'
              AND case_number NOT LIKE 'CASE-DEMO%'
              AND title NOT LIKE '[DEMO FIXTURE]%'
            LIMIT 100
        """)
        rows_age = cursor.fetchall()
        now_utc = datetime.now(timezone.utc)
        ages = []
        for r in rows_age:
            ca = r[0] if not hasattr(r, "keys") else r["created_at"]
            if ca:
                if isinstance(ca, str):
                    try:
                        dt = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                    except Exception:
                        continue
                elif isinstance(ca, datetime):
                    dt = ca
                else:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ages.append((now_utc - dt).total_seconds() / 3600.0)
        avg_inv_age = round(sum(ages) / len(ages), 1) if ages else None
    except Exception:
        avg_inv_age = None

    # 6. Real-time streaming throughput: 0.0 when not actively streaming
    current_tpm = 0.0

    return {
        "transactions_processed": txns_count,
        "scored_transactions": txns_count,
        "total_imported": txns_count,
        "total_unique_accounts": total_accounts,
        "transactions_per_minute": current_tpm,
        "alerts_generated": alerts_count,
        "open_investigations": open_invs,
        "high_priority_cases": high_priority,
        "avg_investigation_age_hours": avg_inv_age,
        "verified_false_positive_rate": fpr,
        "confirmed_fraud_count": confirmed_fraud,
        "investigation_completion_rate": completion_rate
    }

def get_analytics_trends(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    
    # Risk score distribution buckets via indexed/indexed-equivalent risk_band
    cursor.execute("SELECT risk_band, COUNT(*) as cnt FROM transactions GROUP BY risk_band")
    b_rows = cursor.fetchall()
    band_counts = {}
    for r in b_rows:
        band_name = r[0] if not hasattr(r, "keys") else r["risk_band"]
        cnt = r[1] if not hasattr(r, "keys") else r["cnt"]
        if band_name:
            band_counts[str(band_name).upper()] = int(cnt or 0)

    risk_distribution = [
        {"band": "Routine (0-24)", "count": band_counts.get("ROUTINE", 0)},
        {"band": "Low (25-49)", "count": band_counts.get("LOW", 0)},
        {"band": "Elevated (50-74)", "count": band_counts.get("ELEVATED", 0)},
        {"band": "High (75-100)", "count": band_counts.get("HIGH", 0) + band_counts.get("CRITICAL", 0)},
    ]
    
    # Case outcomes (Excluding demo fixtures)
    cursor.execute("""
        SELECT disposition, COUNT(*) as cnt
        FROM investigations
        WHERE disposition IS NOT NULL 
          AND title NOT LIKE '[DEMO FIXTURE]%'
          AND case_number NOT LIKE 'CASE-DEMO%'
        GROUP BY disposition
    """)
    outcomes = [{"disposition": r[0] if not hasattr(r, "keys") else r["disposition"], "count": int(r[1] if not hasattr(r, "keys") else r["cnt"])} for r in cursor.fetchall()]
    
    # Status breakdown (Excluding demo fixtures)
    cursor.execute("""
        SELECT status, COUNT(*) as cnt
        FROM investigations
        WHERE title NOT LIKE '[DEMO FIXTURE]%'
          AND case_number NOT LIKE 'CASE-DEMO%'
        GROUP BY status
    """)
    status_breakdown = [{"status": r[0] if not hasattr(r, "keys") else r["status"], "count": int(r[1] if not hasattr(r, "keys") else r["cnt"])} for r in cursor.fetchall()]
    
    # Alert source counts (Excluding demo fixtures)
    cursor.execute("""
        SELECT source, COUNT(*) as cnt
        FROM alert_findings
        WHERE source != 'DEMO_FIXTURE'
          AND description NOT LIKE '[DEMO FIXTURE]%'
        GROUP BY source
    """)
    sources = [{"source": r[0] if not hasattr(r, "keys") else r["source"], "count": int(r[1] if not hasattr(r, "keys") else r["cnt"])} for r in cursor.fetchall()]

    # Transaction types breakdown
    cursor.execute("""
        SELECT transaction_type, COUNT(*) as cnt
        FROM transactions
        GROUP BY transaction_type
        ORDER BY cnt DESC LIMIT 6
    """)
    tx_types = [{"type": r[0] if not hasattr(r, "keys") else r["transaction_type"], "count": int(r[1] if not hasattr(r, "keys") else r["cnt"])} for r in cursor.fetchall()]

    # Top datasets
    cursor.execute("""
        SELECT dataset_source, COUNT(*) as cnt
        FROM transactions
        GROUP BY dataset_source
    """)
    ds_breakdown = [{"dataset": r[0] if not hasattr(r, "keys") else r["dataset_source"], "count": int(r[1] if not hasattr(r, "keys") else r["cnt"])} for r in cursor.fetchall()]
    
    return {
        "risk_score_distribution": risk_distribution,
        "alerts_by_source": sources,
        "case_outcomes": outcomes,
        "investigation_status_breakdown": status_breakdown,
        "transaction_types": tx_types,
        "dataset_breakdown": ds_breakdown
    }

def get_rule_performance(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT id, rule_code, name FROM detection_rules")
    rules = cursor.fetchall()
    results = []
    for r in rules:
        r_id = r[0] if not hasattr(r, "keys") else r["id"]
        code = r[1] if not hasattr(r, "keys") else r["rule_code"]
        name = r[2] if not hasattr(r, "keys") else r["name"]
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trig,
                SUM(CASE WHEN i.disposition = 'CONFIRMED_FRAUD' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN i.disposition IN ('LEGITIMATE_ACTIVITY', 'FALSE_POSITIVE') THEN 1 ELSE 0 END) as fp
            FROM alert_findings af
            JOIN alerts a ON af.alert_id = a.id
            LEFT JOIN investigation_alerts ia ON ia.alert_id = a.id
            LEFT JOIN investigations i ON ia.investigation_id = i.id
            WHERE af.code = ?
        """, (code,))
        row = cursor.fetchone()
        trig = int((row[0] if not hasattr(row, "keys") else row["total_trig"]) or 0)
        confirmed = int((row[1] if not hasattr(row, "keys") else row["confirmed"]) or 0)
        fp = int((row[2] if not hasattr(row, "keys") else row["fp"]) or 0)
        total_eval = confirmed + fp
        precision = round(confirmed / total_eval, 4) if total_eval > 0 else None

        results.append({
            "rule_code": code,
            "rule_name": name,
            "trigger_count": trig,
            "confirmed_fraud_count": confirmed,
            "false_positive_count": fp,
            "precision": precision,
            "is_sufficient_sample": trig >= 10
        })
    return results
