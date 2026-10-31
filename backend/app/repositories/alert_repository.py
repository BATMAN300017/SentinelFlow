import sqlite3
import json
from app.utils.json_utils import safe_json_loads, safe_json_dumps
from typing import Dict, Any, List, Optional, Tuple
from app.utils.ids import generate_alert_id
from app.utils.time import utc_now_iso

def create_alert(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    alert_id = data.get("id") or generate_alert_id()
    alert_ref = data.get("alert_ref") or f"ALT-{alert_id[-6:].upper()}"
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (
            id, alert_ref, transaction_id, account_id, customer_id,
            severity, status, risk_score, title, summary, assigned_to,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_id, alert_ref, data["transaction_id"], data["account_id"],
        data["customer_id"], data["severity"], data.get("status", "NEW"),
        float(data["risk_score"]), data["title"], data["summary"],
        data.get("assigned_to"), now, now
    ))
    
    # Save findings
    findings = data.get("findings", [])
    for f in findings:
        f_id = f.get("id") or f"FND-{generate_alert_id()[-6:]}"
        feat_json = safe_json_dumps(f.get("feature_values", {}))
        cursor.execute("""
            INSERT INTO alert_findings (id, alert_id, source, code, description, score_contribution, feature_values_json, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f_id, alert_id, f.get("source", "RULE"), f.get("code", "UNKNOWN"), f.get("description", ""), float(f.get("score_contribution", 0.0)), feat_json, f.get("version", "v1"), now))
        
    return {**data, "id": alert_id, "alert_ref": alert_ref, "created_at": now, "updated_at": now}

def get_alert_by_id(conn: sqlite3.Connection, alert_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.id, a.alert_ref, a.transaction_id, a.account_id, a.customer_id,
            a.severity, a.status, a.risk_score, a.title, a.summary, a.assigned_to,
            a.dismissal_reason, a.created_at, a.updated_at, a.alert_type, a.detection_reason,
            t.source_account_id, t.destination_account_id, t.beneficiary_name, 
            t.amount as transaction_amount, t.currency, t.payment_channel, 
            t.transaction_timestamp, t.dataset_source,
            acc.account_type, acc.balance as account_balance
        FROM alerts a
        LEFT JOIN transactions t ON a.transaction_id = t.id
        LEFT JOIN accounts acc ON a.account_id = acc.id
        WHERE a.id = ? OR a.alert_ref = ?
        LIMIT 1
    """, (alert_id, alert_id))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row._dict if hasattr(row, "_dict") else row)
    score = float(d.get("risk_score") or 0.0)
    amt = float(d.get("transaction_amount") or 0.0)
    
    cursor.execute("SELECT * FROM alert_findings WHERE alert_id = ?", (d["id"],))
    findings = []
    for f_row in cursor.fetchall():
        f_dict = dict(f_row._dict if hasattr(f_row, "_dict") else f_row)
        f_dict["score_contribution"] = float(f_dict.get("score_contribution") or 0.0)
        f_dict["feature_values"] = safe_json_loads(f_dict.get("feature_values_json"), {})
        findings.append(f_dict)
        
    return {
        "id": d["id"],
        "alert_ref": d.get("alert_ref") or d["id"],
        "transaction_id": d.get("transaction_id") or "TXN-UNKNOWN",
        "source_account": d.get("account_id") or d.get("source_account_id") or "UNKNOWN",
        "account_id": d.get("account_id") or d.get("source_account_id") or "UNKNOWN",
        "destination_account": d.get("destination_account_id") or "UNKNOWN_COUNTERPARTY",
        "destination_account_id": d.get("destination_account_id") or "UNKNOWN_COUNTERPARTY",
        "transaction_amount": amt,
        "amount": amt,
        "currency": d.get("currency") or "INR",
        "transaction_timestamp": str(d.get("transaction_timestamp") or d.get("created_at") or ""),
        "predicted_risk_score": score,
        "risk_score": score,
        "predicted_risk_category": d.get("severity") or "MEDIUM",
        "severity": d.get("severity") or "MEDIUM",
        "detection_reason": d.get("detection_reason") or d.get("summary") or d.get("title") or "Suspicious behavioral anomaly detected",
        "detection_method": d.get("alert_type") or "ENSEMBLE (Rules + Random Forest + MAD + Isolation Forest + Graph)",
        "alert_type": d.get("alert_type") or "ENSEMBLE",
        "dataset_provenance": d.get("dataset_source") or "NFPC",
        "dataset_source": d.get("dataset_source") or "NFPC",
        "investigation_status": d.get("status") or "NEW",
        "status": d.get("status") or "NEW",
        "title": d.get("title") or "Suspicious Transaction Alert",
        "summary": d.get("summary") or "",
        "customer_id": d.get("customer_id"),
        "assigned_to": d.get("assigned_to"),
        "payment_channel": d.get("payment_channel") or "IMPS",
        "beneficiary_name": d.get("beneficiary_name") or "External Counterparty",
        "created_at": str(d.get("created_at") or ""),
        "updated_at": str(d.get("updated_at") or ""),
        "findings": findings
    }

def list_alerts(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    dataset: Optional[str] = None,
    detection_method: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    cursor = conn.cursor()
    base_from = """
        FROM alerts a
        LEFT JOIN transactions t ON a.transaction_id = t.id
        LEFT JOIN accounts acc ON a.account_id = acc.id
        WHERE 1=1
    """
    params = []
    where_clauses = ""
    
    if severity and severity.upper() != "ALL":
        where_clauses += " AND UPPER(a.severity) = ?"
        params.append(severity.upper())
        
    if status and status.upper() != "ALL":
        where_clauses += " AND UPPER(a.status) = ?"
        params.append(status.upper())
        
    if dataset and dataset.upper() != "ALL":
        where_clauses += " AND UPPER(COALESCE(t.dataset_source, '')) = ?"
        params.append(dataset.upper())
        
    if detection_method and detection_method.upper() != "ALL":
        where_clauses += " AND (UPPER(COALESCE(a.alert_type, '')) = ? OR UPPER(COALESCE(a.detection_reason, '')) LIKE ?)"
        params.extend([detection_method.upper(), f"%{detection_method.upper()}%"])
        
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        where_clauses += """ AND (
            LOWER(a.id) LIKE ? OR 
            LOWER(COALESCE(a.alert_ref, '')) LIKE ? OR 
            LOWER(COALESCE(a.transaction_id, '')) LIKE ? OR 
            LOWER(COALESCE(a.account_id, '')) LIKE ? OR 
            LOWER(COALESCE(t.destination_account_id, '')) LIKE ? OR
            LOWER(COALESCE(a.title, '')) LIKE ?
        )"""
        params.extend([term, term, term, term, term, term])
        
    count_query = f"SELECT COUNT(a.id) {base_from} {where_clauses}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    query = f"""
        SELECT 
            a.id, a.alert_ref, a.transaction_id, a.account_id, a.customer_id,
            a.severity, a.status, a.risk_score, a.title, a.summary, a.assigned_to,
            a.dismissal_reason, a.created_at, a.updated_at, a.alert_type, a.detection_reason,
            t.source_account_id, t.destination_account_id, t.beneficiary_name, 
            t.amount as transaction_amount, t.currency, t.payment_channel, 
            t.transaction_timestamp, t.dataset_source,
            acc.account_type, acc.balance as account_balance
        {base_from} {where_clauses}
        ORDER BY a.risk_score DESC, a.created_at DESC
        LIMIT ? OFFSET ?
    """
    query_params = list(params)
    query_params.extend([limit, offset])
    
    cursor.execute(query, query_params)
    raw_rows = cursor.fetchall()
    
    items = []
    for r in raw_rows:
        d = dict(r._dict if hasattr(r, "_dict") else r)
        score = float(d.get("risk_score") or 0.0)
        amt = float(d.get("transaction_amount") or 0.0)
        
        item = {
            "id": d["id"],
            "alert_ref": d.get("alert_ref") or d["id"],
            "transaction_id": d.get("transaction_id") or "TXN-UNKNOWN",
            "source_account": d.get("account_id") or d.get("source_account_id") or "UNKNOWN",
            "account_id": d.get("account_id") or d.get("source_account_id") or "UNKNOWN",
            "destination_account": d.get("destination_account_id") or "UNKNOWN_COUNTERPARTY",
            "destination_account_id": d.get("destination_account_id") or "UNKNOWN_COUNTERPARTY",
            "transaction_amount": amt,
            "amount": amt,
            "currency": d.get("currency") or "INR",
            "transaction_timestamp": str(d.get("transaction_timestamp") or d.get("created_at") or ""),
            "predicted_risk_score": score,
            "risk_score": score,
            "predicted_risk_category": d.get("severity") or "MEDIUM",
            "severity": d.get("severity") or "MEDIUM",
            "detection_reason": d.get("detection_reason") or d.get("summary") or d.get("title") or "Suspicious behavioral anomaly detected",
            "detection_method": d.get("alert_type") or "ENSEMBLE (Rules + Random Forest + MAD + Isolation Forest + Graph)",
            "alert_type": d.get("alert_type") or "ENSEMBLE",
            "dataset_provenance": d.get("dataset_source") or "NFPC",
            "dataset_source": d.get("dataset_source") or "NFPC",
            "investigation_status": d.get("status") or "NEW",
            "status": d.get("status") or "NEW",
            "title": d.get("title") or "Suspicious Transaction Alert",
            "summary": d.get("summary") or "",
            "customer_id": d.get("customer_id"),
            "assigned_to": d.get("assigned_to"),
            "payment_channel": d.get("payment_channel") or "IMPS",
            "beneficiary_name": d.get("beneficiary_name") or "External Counterparty",
            "created_at": str(d.get("created_at") or ""),
            "updated_at": str(d.get("updated_at") or "")
        }
        items.append(item)
        
    return items, total
