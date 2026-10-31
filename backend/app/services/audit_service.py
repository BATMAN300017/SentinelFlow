import sqlite3
import json
from typing import Optional, Dict, Any
from app.utils.ids import generate_id
from app.utils.time import utc_now_iso
from app.utils.json_utils import safe_json_dumps
from app.core.logging import logger

def record_audit_event(
    conn: sqlite3.Connection,
    actor_id: Optional[str],
    actor_name: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    request_ip: Optional[str] = None
):
    ev_id = generate_id("AUD")
    now = utc_now_iso()
    meta_json = safe_json_dumps(metadata or {})
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_events (id, actor_id, actor_name, action, resource_type, resource_id, request_ip, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ev_id, actor_id, actor_name or "SYSTEM", action, resource_type, resource_id, request_ip, meta_json, now))
    
    logger.info(f"Audit event recorded: {action} on {resource_type}:{resource_id} by {actor_name or 'SYSTEM'}")
