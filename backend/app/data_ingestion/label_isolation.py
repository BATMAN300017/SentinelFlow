"""
Strict Label Isolation Subsystem.

Enforces physical and logical isolation between:
- Pipeline A: Unsupervised Detection Engine (STRICTLY NO LABELS).
- Pipeline B: Independent Evaluation Engine (Protected Ground-Truth Store).

Any attempted leak of ground-truth fraud or mule labels into detection features,
APIs, or models immediately raises a LabelLeakageError.
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional, Set, Tuple
from app.core.logging import logger

class LabelLeakageError(Exception):
    """Raised when a protected ground-truth label field attempts to leak into Pipeline A."""
    pass

# Whitelist of fields permitted in Pipeline A (Detection Engine)
DETECTION_ALLOWED_FIELDS: Set[str] = {
    "id",
    "event_id",
    "source_account_id",
    "destination_account_id",
    "amount",
    "currency",
    "created_at",
    "sender_bank",
    "receiver_bank",
    "sender_country",
    "receiver_country",
    "payment_channel",
    "payment_type",
    "converted_amount",
    "converted_currency",
    "exchange_rate",
    "exchange_rate_source",
    "exchange_rate_timestamp",
    "device_id",
    "ip_address",
    "beneficiary_name",
    "dataset_source",
    "batch_id",
    "status",
    "account_number",
    "customer_id",
    "account_type",
    "balance",
    "is_dormant"
}

# Blacklist of protected ground-truth fields forbidden in Pipeline A
PROTECTED_LABEL_FIELDS: Set[str] = {
    "is_laundering",
    "is_fraud",
    "is_mule",
    "mule_label",
    "laundering_type",
    "fraud_label",
    "ground_truth_label",
    "is_ground_truth_fraud",
    "typology",
    "hidden_test_outcome",
    "scam_category",
    "target_label",
    "class_label",
    "label"
}

PROTECTED_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "protected_labels")
)

def init_protected_store():
    """Ensure the physical directory and protected storage database exist."""
    os.makedirs(PROTECTED_STORAGE_DIR, exist_ok=True)
    db_path = os.path.join(PROTECTED_STORAGE_DIR, "protected_ground_truth.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protected_transaction_labels (
            transaction_id TEXT PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            is_laundering INTEGER,
            laundering_type TEXT,
            raw_labels_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protected_account_labels (
            account_id TEXT PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            is_mule INTEGER,
            mule_role TEXT,
            raw_labels_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protected_scenario_labels (
            scenario_id TEXT PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            typology TEXT NOT NULL,
            mule_account_ids_json TEXT NOT NULL,
            victim_account_ids_json TEXT NOT NULL,
            beneficiary_account_ids_json TEXT NOT NULL,
            laundering_hops_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def assert_no_label_leakage(record: Dict[str, Any], context: str = "Pipeline A"):
    """
    Validates that a dictionary (features, transaction payload, API response)
    contains NO protected ground-truth labels.
    """
    for key in record.keys():
        key_lower = key.lower()
        if key_lower in PROTECTED_LABEL_FIELDS:
            raise LabelLeakageError(
                f"[SECURITY ALERT] Label leakage detected in {context}! "
                f"Field '{key}' is a protected ground-truth label and MUST NOT be accessed by detection."
            )

def strip_labels_for_detection(record: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Splits an incoming raw dataset record into:
    1. A clean, label-free dictionary for Pipeline A (Detection).
    2. A protected ground-truth dictionary for Pipeline B (Evaluation).
    """
    detection_record = {}
    protected_labels = {}

    for k, v in record.items():
        k_lower = k.lower()
        if k_lower in PROTECTED_LABEL_FIELDS:
            protected_labels[k] = v
        else:
            detection_record[k] = v

    # Final assertion: guarantee zero leakage into the detection record
    assert_no_label_leakage(detection_record, context="strip_labels_for_detection")
    return detection_record, protected_labels

def store_protected_transaction_label(
    transaction_id: str,
    dataset_name: str = "DEFAULT",
    is_laundering: Optional[int] = None,
    laundering_type: Optional[str] = None,
    raw_labels: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    ground_truth_label: Optional[int] = None,
    scenario_id: Optional[str] = None,
    conn: Optional[Any] = None
):
    """Store transaction ground-truth strictly in the isolated evaluation store."""
    if is_laundering is None and ground_truth_label is not None:
        is_laundering = ground_truth_label
    if laundering_type is None and scenario_id is not None:
        laundering_type = scenario_id
    if raw_labels is None:
        raw_labels = {"label": is_laundering, "scenario": laundering_type}
    if timestamp is None:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

    init_protected_store()
    if conn is not None:
        try:
            pcursor = conn.cursor()
            pcursor.execute("""
                INSERT INTO protected_transaction_labels 
                (transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (transaction_id) DO UPDATE SET 
                    is_laundering = EXCLUDED.is_laundering,
                    laundering_type = EXCLUDED.laundering_type,
                    raw_labels_json = EXCLUDED.raw_labels_json;
            """, (transaction_id, dataset_name, is_laundering, laundering_type, json.dumps(raw_labels), timestamp))
        except Exception as e:
            logger.debug(f"Could not persist transaction label to provided connection: {e}")

    try:
        db_path = os.path.join(PROTECTED_STORAGE_DIR, "protected_ground_truth.db")
        sconn = sqlite3.connect(db_path)
        cursor = sconn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO protected_transaction_labels 
            (transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transaction_id, dataset_name, is_laundering, laundering_type, json.dumps(raw_labels), timestamp))
        sconn.commit()
        sconn.close()
    except Exception as e:
        logger.debug(f"Could not persist transaction label to SQLite: {e}")

def store_protected_account_label(
    account_id: str,
    dataset_name: str,
    is_mule: Optional[int],
    mule_role: Optional[str],
    raw_labels: Dict[str, Any],
    timestamp: str
):
    """Store account ground-truth strictly in the isolated evaluation store."""
    init_protected_store()
    db_path = os.path.join(PROTECTED_STORAGE_DIR, "protected_ground_truth.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO protected_account_labels 
        (account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (account_id, dataset_name, is_mule, mule_role, json.dumps(raw_labels), timestamp))
    conn.commit()
    conn.close()

def store_protected_scenario_label(
    scenario_id: str,
    dataset_name: str,
    typology: str,
    mule_account_ids: List[str],
    victim_account_ids: List[str],
    beneficiary_account_ids: List[str],
    laundering_hops: List[Dict[str, Any]],
    timestamp: str
):
    """Store complete multi-hop scenario ground-truth strictly in the isolated evaluation store."""
    init_protected_store()
    db_path = os.path.join(PROTECTED_STORAGE_DIR, "protected_ground_truth.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO protected_scenario_labels
        (scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, 
         beneficiary_account_ids_json, laundering_hops_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scenario_id,
        dataset_name,
        typology,
        json.dumps(mule_account_ids),
        json.dumps(victim_account_ids),
        json.dumps(beneficiary_account_ids),
        json.dumps(laundering_hops),
        timestamp
    ))
    conn.commit()
    conn.close()

def get_protected_evaluation_labels(dataset_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Reads ground-truth labels for comparison against detection predictions.
    Queries isolated local SQLite store first for instant zero-latency retrieval,
    falling back to Supabase PostgreSQL.
    """
    txn_rows, acc_rows, scen_rows = [], [], []

    # 1. Read from isolated local SQLite vault first (fast, reliable, zero network latency)
    try:
        init_protected_store()
        db_path = os.path.join(PROTECTED_STORAGE_DIR, "protected_ground_truth.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            if dataset_name:
                cursor.execute("SELECT transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at FROM protected_transaction_labels WHERE dataset_name = ?", (dataset_name,))
                txn_rows = cursor.fetchall()
                cursor.execute("SELECT account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at FROM protected_account_labels WHERE dataset_name = ?", (dataset_name,))
                acc_rows = cursor.fetchall()
                cursor.execute("SELECT scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, beneficiary_account_ids_json, laundering_hops_json, created_at FROM protected_scenario_labels WHERE dataset_name = ?", (dataset_name,))
                scen_rows = cursor.fetchall()
            else:
                cursor.execute("SELECT transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at FROM protected_transaction_labels")
                txn_rows = cursor.fetchall()
                cursor.execute("SELECT account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at FROM protected_account_labels")
                acc_rows = cursor.fetchall()
                cursor.execute("SELECT scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, beneficiary_account_ids_json, laundering_hops_json, created_at FROM protected_scenario_labels")
                scen_rows = cursor.fetchall()
            conn.close()
    except Exception as e:
        logger.error(f"Error reading local SQLite protected store: {e}")

    # 2. Fall back to PostgreSQL if local SQLite returned nothing
    if not txn_rows and not acc_rows and not scen_rows:
        try:
            from app.core.database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if dataset_name:
                    ds_filter = ('NFPC', 'NFPC_MULE') if dataset_name.upper() in ('NFPC', 'NFPC_MULE') else (dataset_name,)
                    if len(ds_filter) == 2:
                        cursor.execute("SELECT transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at FROM protected_transaction_labels WHERE dataset_name IN ('NFPC', 'NFPC_MULE')")
                        txn_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                        cursor.execute("SELECT account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at FROM protected_account_labels WHERE dataset_name IN ('NFPC', 'NFPC_MULE')")
                        acc_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                        cursor.execute("SELECT scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, beneficiary_account_ids_json, laundering_hops_json, created_at FROM protected_scenario_labels WHERE dataset_name IN ('NFPC', 'NFPC_MULE')")
                        scen_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                    else:
                        cursor.execute("SELECT transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at FROM protected_transaction_labels WHERE dataset_name = ?", (dataset_name,))
                        txn_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                        cursor.execute("SELECT account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at FROM protected_account_labels WHERE dataset_name = ?", (dataset_name,))
                        acc_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                        cursor.execute("SELECT scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, beneficiary_account_ids_json, laundering_hops_json, created_at FROM protected_scenario_labels WHERE dataset_name = ?", (dataset_name,))
                        scen_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                else:
                    cursor.execute("SELECT transaction_id, dataset_name, is_laundering, laundering_type, raw_labels_json, created_at FROM protected_transaction_labels")
                    txn_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                    cursor.execute("SELECT account_id, dataset_name, is_mule, mule_role, raw_labels_json, created_at FROM protected_account_labels")
                    acc_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
                    cursor.execute("SELECT scenario_id, dataset_name, typology, mule_account_ids_json, victim_account_ids_json, beneficiary_account_ids_json, laundering_hops_json, created_at FROM protected_scenario_labels")
                    scen_rows = [list(r.values()) if hasattr(r, 'values') else list(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Could not query PostgreSQL for protected labels ({e}).")

    txns = {}
    for r in txn_rows:
        txns[r[0]] = {
            "dataset_name": r[1],
            "is_laundering": r[2],
            "laundering_type": r[3],
            "raw": json.loads(r[4]),
            "created_at": r[5]
        }

    accounts = {}
    for r in acc_rows:
        accounts[r[0]] = {
            "dataset_name": r[1],
            "is_mule": r[2],
            "mule_role": r[3],
            "raw": json.loads(r[4]),
            "created_at": r[5]
        }

    scenarios = {}
    for r in scen_rows:
        scenarios[r[0]] = {
            "dataset_name": r[1],
            "typology": r[2],
            "mule_accounts": json.loads(r[3]),
            "victim_accounts": json.loads(r[4]),
            "beneficiary_accounts": json.loads(r[5]),
            "laundering_hops": json.loads(r[6]),
            "created_at": r[7]
        }

    return {
        "transactions": txns,
        "accounts": accounts,
        "scenarios": scenarios
    }
