import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from app.utils.ids import generate_transaction_id
from app.utils.time import utc_now_iso

def create_transaction(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    txn_id = data.get("id") or generate_transaction_id()
    now = data.get("created_at") or utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (
            id, event_id, source_account_id, destination_account_id, beneficiary_name,
            customer_id, amount, currency, transaction_type, payment_channel,
            merchant_id, device_id, ip_address, status, scenario_id,
            is_ground_truth_fraud, ground_truth_label, risk_score, risk_band, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        txn_id, data["event_id"], data["source_account_id"], data.get("destination_account_id"),
        data.get("beneficiary_name"), data["customer_id"], float(data["amount"]),
        data.get("currency", "USD"), data.get("transaction_type", "TRANSFER"),
        data.get("payment_channel", "ONLINE"), data.get("merchant_id"),
        data.get("device_id"), data.get("ip_address"), data.get("status", "COMPLETED"),
        data.get("scenario_id"), data.get("is_ground_truth_fraud", 0),
        data.get("ground_truth_label"), data.get("risk_score", 0.0),
        data.get("risk_band", "ROUTINE"), now
    ))
    return {**data, "id": txn_id, "created_at": now}

def get_transaction_by_id(conn: sqlite3.Connection, txn_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*,
               CASE 
                   WHEN t.risk_score >= 70.0 THEN 'HIGH_RISK_SUSPICIOUS'
                   WHEN t.risk_score >= 50.0 THEN 'ELEVATED_RISK'
                   ELSE 'NORMAL_CLEARED'
               END AS ai_prediction,
               ROUND(t.risk_score / 100.0, 3) AS ai_confidence,
               t.risk_score AS ai_model_score,
               COALESCE(a.detection_reason, a.summary, 'Standard velocity and behavioral baseline') AS ai_reasons,
               a.id AS linked_alert_id,
               ia.investigation_id AS linked_investigation_id
        FROM transactions t
        LEFT JOIN alerts a ON t.id = a.transaction_id
        LEFT JOIN investigation_alerts ia ON a.id = ia.alert_id
        WHERE t.id = ? OR t.event_id = ?
        LIMIT 1
    """, (txn_id, txn_id))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    # Convert numerical types for JSON serialization
    if d.get("amount") is not None:
        d["amount"] = float(d["amount"])
    if d.get("risk_score") is not None:
        d["risk_score"] = float(d["risk_score"])
    return d

def list_transactions(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    risk_band: Optional[str] = None,
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    channel: Optional[str] = None,
    dataset: Optional[str] = None,
    min_score: Optional[float] = None,
    flow_status: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    cursor = conn.cursor()
    query = """
        SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.currency,
               t.payment_channel, t.status, t.risk_score, t.risk_band, t.created_at,
               t.dataset_source, t.dataset_source AS dataset_id, t.is_ground_truth_fraud, t.ground_truth_label,
               t.customer_id, t.beneficiary_name,
               CASE 
                   WHEN t.risk_score >= 70.0 THEN 'HIGH_RISK_SUSPICIOUS'
                   WHEN t.risk_score >= 50.0 THEN 'ELEVATED_RISK'
                   ELSE 'NORMAL_CLEARED'
               END AS ai_prediction,
               ROUND(t.risk_score / 100.0, 3) AS ai_confidence,
               COALESCE(a.detection_reason, a.summary, 'Standard velocity and behavioral baseline') AS ai_reasons,
               a.id AS linked_alert_id,
               ia.investigation_id AS linked_investigation_id
        FROM transactions t
        LEFT JOIN alerts a ON t.id = a.transaction_id
        LEFT JOIN investigation_alerts ia ON a.id = ia.alert_id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) FROM transactions t WHERE 1=1"
    params: List[Any] = []

    if search:
        search_val = search.strip()
        search_filter = " AND (t.id = ? OR t.source_account_id = ? OR t.destination_account_id = ? OR t.customer_id = ?)"
        query += search_filter
        count_query += search_filter
        params.extend([search_val, search_val, search_val, search_val])

    if risk_band:
        query += " AND t.risk_band = ?"
        count_query += " AND t.risk_band = ?"
        params.append(risk_band.upper())

    if account_id:
        query += " AND (t.source_account_id = ? OR t.destination_account_id = ?)"
        count_query += " AND (t.source_account_id = ? OR t.destination_account_id = ?)"
        params.extend([account_id, account_id])

    if channel:
        query += " AND t.payment_channel = ?"
        count_query += " AND t.payment_channel = ?"
        params.append(channel.upper())

    if dataset:
        query += " AND t.dataset_source = ?"
        count_query += " AND t.dataset_source = ?"
        params.append(dataset)

    if min_score is not None:
        query += " AND t.risk_score >= ?"
        count_query += " AND t.risk_score >= ?"
        params.append(float(min_score))

    if flow_status and flow_status.upper() != "ALL":
        fs = flow_status.upper()
        if fs == "SUSPICIOUS":
            query += " AND (t.risk_score >= 50.0 OR t.risk_band IN ('ELEVATED', 'HIGH', 'CRITICAL'))"
            count_query += " AND (t.risk_score >= 50.0 OR t.risk_band IN ('ELEVATED', 'HIGH', 'CRITICAL'))"
        elif fs == "FLAGGED":
            query += " AND (a.id IS NOT NULL OR t.risk_score >= 70.0)"
            count_query += " AND (t.id IN (SELECT transaction_id FROM alerts WHERE transaction_id IS NOT NULL) OR t.risk_score >= 70.0)"
        elif fs == "BLOCKED":
            query += " AND t.status IN ('BLOCKED', 'DECLINED', 'REJECTED')"
            count_query += " AND t.status IN ('BLOCKED', 'DECLINED', 'REJECTED')"
        elif fs == "CLEARED":
            query += " AND (t.status = 'COMPLETED' AND t.risk_score < 40.0)"
            count_query += " AND (t.status = 'COMPLETED' AND t.risk_score < 40.0)"

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        if d.get("amount") is not None:
            d["amount"] = float(d["amount"])
        if d.get("risk_score") is not None:
            d["risk_score"] = float(d["risk_score"])
        rows.append(d)

    return rows, total
