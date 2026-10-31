import sqlite3
import json
import hashlib
from typing import Dict, Any, List, Optional
from app.utils.ids import generate_evidence_id
from app.utils.time import utc_now_iso
from app.utils.json_utils import safe_json_loads, safe_json_dumps

def create_evidence(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    ev_id = data.get("id") or generate_evidence_id()
    now = utc_now_iso()
    
    observed_str = safe_json_dumps(data.get("observed_facts", {}))
    entities_str = safe_json_dumps(data.get("associated_entities", []))
    txns_str = safe_json_dumps(data.get("associated_transactions", []))
    
    # Compute integrity hash
    hash_payload = f"{data['investigation_id']}_{data['evidence_type']}_{observed_str}_{now}"
    integrity_hash = hashlib.sha256(hash_payload.encode()).hexdigest()
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO evidence_items (
            id, investigation_id, evidence_type, source_record_id,
            description, observed_facts_json, associated_entities_json,
            associated_transactions_json, verification_status, collector,
            integrity_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ev_id, data["investigation_id"], data["evidence_type"], data.get("source_record_id"),
        data["description"], observed_str, entities_str, txns_str,
        data.get("verification_status", "SUPPORTING"), data.get("collector", "ANALYST"),
        integrity_hash, now
    ))
    
    # Update case completeness score
    update_case_completeness(conn, data["investigation_id"])
    
    return {
        **data,
        "id": ev_id,
        "integrity_hash": integrity_hash,
        "created_at": now
    }

def list_evidence_for_case(conn: sqlite3.Connection, investigation_id: str) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evidence_items WHERE investigation_id = ? ORDER BY created_at ASC", (investigation_id,))
    rows = cursor.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["observed_facts"] = safe_json_loads(d.get("observed_facts_json"), {})
        d["associated_entities"] = safe_json_loads(d.get("associated_entities_json"), [])
        d["associated_transactions"] = safe_json_loads(d.get("associated_transactions_json"), [])
        items.append(d)
    return items

def update_case_completeness(conn: sqlite3.Connection, investigation_id: str):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT evidence_type FROM evidence_items WHERE investigation_id = ?", (investigation_id,))
    types = {r[0] for r in cursor.fetchall()}
    
    # Standard checklist types: TRANSACTION, BEHAVIORAL_ANOMALY, RULE_MATCH, RELATIONSHIP, TIMELINE_EVENT
    target_types = {"TRANSACTION", "BEHAVIORAL_ANOMALY", "RULE_MATCH", "RELATIONSHIP", "TIMELINE_EVENT"}
    matched = len(types.intersection(target_types))
    score = round((matched / len(target_types)) * 100.0, 1)
    
    cursor.execute("UPDATE investigations SET evidence_completeness_score = ? WHERE id = ?", (score, investigation_id))
