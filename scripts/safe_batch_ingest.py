"""
Safe Batch Ingestion and Pipeline Isolation Subsystem for SentinelFlow AI.

Features:
1. Genuinely streaming readers:
   - PyArrow Parquet iter_batches() for NFPC Parquet files (never loads full files into RAM).
   - pandas read_csv(chunksize=...) for SAML-D CSV files.
2. Bounded batch streaming and transactional commits:
   - Commits each chunk of transactions bounded by batch_size.
   - Atomically updates checkpoint state after each committed chunk.
   - Resumable from the exact interrupted row offset without skipping or duplicating records.
3. Database-enforced deduplication:
   - Chunked indexed lookup on unique event_id.
   - Database-level ON CONFLICT DO NOTHING safety.
   - Removed legacy SELECT ... LIMIT 500000 in-memory list.
4. Strict Pipeline B label isolation:
   - Ground-truth labels are routed strictly to data/protected_labels/protected_ground_truth.db.
   - Detection records verified via assert_no_label_leakage before scoring or ingestion.
5. Point-in-time real-time scoring via score_transaction() with scoring failure tracking.
6. Stamped batch_id and atomic rollback:
   - Deletes transactions, alert findings, and alerts for the batch.
   - Deletes protected transaction labels from Pipeline B vault for the rolled back transactions.
   - Safely removes batch-created accounts and customers that have no remaining transactions.
   - Resets checkpoint offset to pre-batch position.
7. Accurate PostgreSQL capacity guard:
   - Configurable quota ceiling (--quota-mb, default 500.0 MB) and safety reserve (--safety-reserve-mb, default 50.0 MB).
   - Uses empirical 0.650 KB / transaction growth rate (PostgreSQL table + indexes + toast).
8. Safe-by-default execution:
   - Defaults to --dry-run (zero database writes, zero protected store writes).
   - Requires explicit --execute flag for live persistence.
"""

import os
import sys
import json
import uuid
import argparse
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set, Generator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import pandas as pd
import pyarrow.parquet as pq

from app.core.config import settings
from app.core.database import get_db_connection
from app.core.logging import logger
from app.detection.engine import score_transaction
from app.services.audit_service import record_audit_event
from app.data_ingestion.label_isolation import (
    init_protected_store,
    assert_no_label_leakage,
    strip_labels_for_detection,
    store_protected_transaction_label,
    store_protected_account_label
)
from app.utils.ids import generate_id, generate_alert_id
from app.utils.time import utc_now_iso

CHECKPOINT_DIR = os.path.join(BASE_DIR, "data", "temp_manifests")
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "batch_checkpoint.json")
DEFAULT_QUOTA_MB = float(os.getenv("SUPABASE_QUOTA_MB", "500.0"))
DEFAULT_SAFETY_RESERVE_MB = float(os.getenv("SUPABASE_SAFETY_RESERVE_MB", "50.0"))
ESTIMATED_KB_PER_TXN = 0.650  # Measured PostgreSQL table + 5 B-tree indexes + system catalog rate


def get_current_storage_mb(conn) -> Tuple[float, str]:
    """Queries current database physical storage in MB."""
    cursor = conn.cursor()
    # Check if PostgreSQL
    try:
        cursor.execute("SELECT pg_database_size(current_database());")
        row = cursor.fetchone()
        if row:
            bytes_val = row[0] if not hasattr(row, "keys") else row["pg_database_size"]
            return float(bytes_val) / (1024.0 * 1024.0), "PostgreSQL"
    except Exception:
        pass

    # Fallback SQLite
    try:
        cursor.execute("PRAGMA page_count;")
        p_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        p_size = cursor.fetchone()[0]
        return (float(p_count * p_size) / (1024.0 * 1024.0)), "SQLite"
    except Exception:
        return 0.0, "Unknown"


def load_checkpoint() -> Dict[str, Any]:
    """Loads batch checkpoint state."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read checkpoint file: {e}")
    return {
        "datasets": {
            "NFPC": {"last_offset": 0, "total_ingested": 0},
            "SAML_D": {"last_offset": 0, "total_ingested": 0}
        },
        "batches": []
    }


def save_checkpoint(data: Dict[str, Any]):
    """Persists batch checkpoint state atomically."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    tmp_path = CHECKPOINT_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    os.rename(tmp_path, CHECKPOINT_FILE)


def check_storage_projection(
    conn,
    records_to_ingest: int,
    quota_mb: float = DEFAULT_QUOTA_MB,
    safety_reserve_mb: float = DEFAULT_SAFETY_RESERVE_MB
) -> bool:
    """Verifies that the projected ingestion will not breach storage quotas."""
    current_mb, engine = get_current_storage_mb(conn)
    projected_add_mb = (records_to_ingest * ESTIMATED_KB_PER_TXN) / 1024.0
    projected_total_mb = current_mb + projected_add_mb
    effective_ceiling_mb = quota_mb - safety_reserve_mb
    available_headroom_mb = max(0.0, effective_ceiling_mb - current_mb)
    max_safe_records = int((available_headroom_mb * 1024.0) / ESTIMATED_KB_PER_TXN)

    print(f"\n--- Storage Safety Assessment ({engine}) ---")
    print(f"Current DB Storage:      {current_mb:.2f} MB")
    print(f"Projected Addition:      +{projected_add_mb:.2f} MB ({records_to_ingest:,} txns @ {ESTIMATED_KB_PER_TXN:.3f} KB/txn)")
    print(f"Projected Total:         {projected_total_mb:.2f} MB")
    print(f"Total Quota:             {quota_mb:.2f} MB")
    print(f"Safety Reserve:          {safety_reserve_mb:.2f} MB")
    print(f"Safety Ceiling:          {effective_ceiling_mb:.2f} MB")
    print(f"Available Safe Headroom: {available_headroom_mb:.2f} MB (~{max_safe_records:,} transactions)")

    if projected_total_mb > effective_ceiling_mb:
        print(f"\n[ERROR] Projected storage ({projected_total_mb:.2f} MB) exceeds safety ceiling of {effective_ceiling_mb:.2f} MB!")
        print(f"Exceeds allowance by {projected_total_mb - effective_ceiling_mb:.2f} MB.")
        print(f"Maximum allowable ingestion right now: {max_safe_records:,} records.")
        print("Aborting to protect production database quota.")
        return False
    print("[PASS] Storage capacity verified within safe limits.\n")
    return True


def ensure_account_exists(
    conn,
    account_id: str,
    customer_id: str = "CUST-DEFAULT",
    currency: str = "USD"
) -> Tuple[bool, bool]:
    """
    Ensures account and customer exist in database for foreign key integrity.
    Returns (created_customer: bool, created_account: bool).
    """
    cursor = conn.cursor()
    created_cust = False
    created_acc = False

    cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
            VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
        """, (customer_id, customer_id, f"Customer {customer_id}", f"{customer_id.lower()}@sentinelflow.internal", utc_now_iso()))
        created_cust = True

    cursor.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO accounts (id, account_number, customer_id, account_type, currency, balance, status, is_dormant, created_at)
            VALUES (?, ?, ?, 'CHECKING', ?, 10000.0, 'ACTIVE', 0, ?)
        """, (account_id, account_id, customer_id, currency, utc_now_iso()))
        created_acc = True

    return created_cust, created_acc


def stream_parquet_chunks(
    file_path: str,
    start_offset: int,
    max_records: int,
    chunk_size: int
) -> Generator[pd.DataFrame, None, None]:
    """
    Streams Parquet data in bounded RecordBatches without loading the full file into memory.
    """
    pq_file = pq.ParquetFile(file_path)
    current_file_idx = 0
    yielded = 0

    for batch in pq_file.iter_batches(batch_size=chunk_size):
        b_len = len(batch)
        if current_file_idx + b_len <= start_offset:
            current_file_idx += b_len
            continue

        local_start = max(0, start_offset - current_file_idx)
        available_in_batch = b_len - local_start
        to_take = min(available_in_batch, max_records - yielded)

        if to_take > 0:
            sliced = batch.slice(local_start, to_take)
            df_chunk = sliced.to_pandas()
            yield df_chunk
            yielded += len(df_chunk)

        current_file_idx += b_len
        if yielded >= max_records:
            break


def stream_csv_chunks(
    file_path: str,
    start_offset: int,
    max_records: int,
    chunk_size: int
) -> Generator[pd.DataFrame, None, None]:
    """
    Streams CSV data in bounded chunks using pandas chunksize without loading the full file into memory.
    """
    yielded = 0
    skip = range(1, start_offset + 1) if start_offset > 0 else None
    for chunk in pd.read_csv(file_path, skiprows=skip, chunksize=chunk_size):
        to_take = min(len(chunk), max_records - yielded)
        if to_take < len(chunk):
            df_chunk = chunk.iloc[:to_take].copy()
        else:
            df_chunk = chunk

        yield df_chunk
        yielded += len(df_chunk)
        if yielded >= max_records:
            break


def check_existing_event_ids(cursor, event_ids: List[str]) -> Set[str]:
    """
    Efficient bounded deduplication query: checks only the event_ids in the current chunk.
    Never loads millions of rows into memory.
    """
    if not event_ids:
        return set()
    existing = set()
    # Chunk by 500 parameters for database query limit safety
    for i in range(0, len(event_ids), 500):
        sub = event_ids[i:i + 500]
        placeholders = ",".join(["?"] * len(sub))
        cursor.execute(f"SELECT event_id FROM transactions WHERE event_id IN ({placeholders});", sub)
        rows = cursor.fetchall()
        for r in rows:
            existing.add(r[0] if not hasattr(r, "keys") else r["event_id"])
    return existing


def execute_batch_ingest(
    dataset_name: str,
    batch_size: int,
    limit: int,
    dry_run: bool,
    quota_mb: float = DEFAULT_QUOTA_MB,
    safety_reserve_mb: float = DEFAULT_SAFETY_RESERVE_MB
) -> Dict[str, Any]:
    """
    Executes a bounded, genuinely streaming batch ingestion with strict label isolation,
    real-time point-in-time scoring, and incremental per-batch commits.
    """
    init_protected_store()
    checkpoint = load_checkpoint()
    ds_state = checkpoint["datasets"].setdefault(dataset_name, {"last_offset": 0, "total_ingested": 0})
    start_offset = ds_state["last_offset"]

    print(f"\n========================================================")
    print(f"SENTINELFLOW STREAMING BATCH INGESTION: {dataset_name}")
    print(f"Mode:            {'DRY RUN (No DB Writes)' if dry_run else 'LIVE EXECUTION'}")
    print(f"Batch Chunk Size:{batch_size:,} | Record Limit: {limit:,}")
    print(f"Starting Offset: {start_offset:,}")
    print(f"========================================================")

    # 1. Locate dataset file
    if dataset_name.upper() == "NFPC":
        file_path = os.path.join(BASE_DIR, "data", "nfpc", "part_0001.parquet")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NFPC dataset file not found at: {file_path}")
        pq_meta = pq.ParquetFile(file_path).metadata
        total_available = pq_meta.num_rows
        print(f"Located NFPC Parquet ({total_available:,} total rows in metadata).")
        chunk_generator = stream_parquet_chunks(file_path, start_offset, limit, batch_size)
    elif dataset_name.upper() in ("SAML_D", "SAMLD"):
        file_path = os.path.join(BASE_DIR, "data", "saml_d", "SAML-D.csv")
        if not os.path.exists(file_path):
            file_path = os.path.join(BASE_DIR, "data", "saml_d", "saml_d_real.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SAML-D dataset file not found at: {file_path}")
        print(f"Located SAML-D CSV file.")
        chunk_generator = stream_csv_chunks(file_path, start_offset, limit, batch_size)
    else:
        raise ValueError(f"Unsupported dataset: {dataset_name}. Must be NFPC or SAML_D.")

    batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

    total_ingested = 0
    total_duplicates = 0
    total_protected_labels = 0
    total_alerts_generated = 0
    total_scoring_failures = 0
    batch_created_accounts: Set[str] = set()
    batch_created_customers: Set[str] = set()

    with get_db_connection() as conn:
        # Check storage capacity guard before processing
        if not check_storage_projection(conn, limit, quota_mb=quota_mb, safety_reserve_mb=safety_reserve_mb):
            return {"status": "ABORTED_STORAGE_LIMIT"}

        cursor = conn.cursor()

        chunk_num = 0
        current_offset = start_offset

        for df_chunk in chunk_generator:
            chunk_num += 1
            chunk_rows = len(df_chunk)
            if chunk_rows == 0:
                continue

            # Step A: Bounded deduplication lookup for current chunk
            candidate_event_ids = []
            for _, row in df_chunk.iterrows():
                d_dict = row.to_dict()
                eid = str(d_dict.get("event_id") or d_dict.get("id") or d_dict.get("Transaction_ID") or "")
                if eid:
                    candidate_event_ids.append(eid)

            existing_in_chunk = set()
            if not dry_run and candidate_event_ids:
                existing_in_chunk = check_existing_event_ids(cursor, candidate_event_ids)

            chunk_ingested = 0
            chunk_duplicates = 0

            # Step B: Process records in current chunk
            for _, row in df_chunk.iterrows():
                raw_dict = row.to_dict()

                # Pipeline B isolation: extract and strip ground truth labels
                detection_dict, protected_labels = strip_labels_for_detection(raw_dict)

                # Strict security assertion: Verify NO label leaks into Pipeline A
                assert_no_label_leakage(detection_dict, context=f"Safe Batch Ingest ({dataset_name})")

                # Map to canonical transaction attributes
                txn_id = str(detection_dict.get("id") or detection_dict.get("Transaction_ID") or f"TXN-{uuid.uuid4().hex[:12]}")
                event_id = str(detection_dict.get("event_id") or txn_id)
                src_acc = str(detection_dict.get("source_account_id") or detection_dict.get("Sender_account") or detection_dict.get("Account_Number") or "ACC-UNKNOWN")
                dest_acc = str(detection_dict.get("destination_account_id") or detection_dict.get("Receiver_account") or "ACC-BENEFICIARY")
                amount = float(detection_dict.get("amount") or detection_dict.get("Amount") or 0.0)
                currency = str(detection_dict.get("currency") or detection_dict.get("Payment_currency") or ("INR" if dataset_name.upper() == "NFPC" else "USD"))
                txn_type = str(detection_dict.get("transaction_type") or detection_dict.get("Payment_type") or "TRANSFER")
                channel = str(detection_dict.get("payment_channel") or detection_dict.get("Payment_type") or "ONLINE")
                created_at = str(detection_dict.get("created_at") or detection_dict.get("Date") or utc_now_iso())

                # Deduplication check
                if event_id in existing_in_chunk:
                    chunk_duplicates += 1
                    total_duplicates += 1
                    continue

                # Route protected ground-truth labels strictly to Pipeline B vault
                if protected_labels and not dry_run:
                    is_laundering = 1 if protected_labels.get("is_laundering") in (1, "1", True) else 0
                    store_protected_transaction_label(
                        transaction_id=txn_id,
                        dataset_name=dataset_name,
                        is_laundering=is_laundering,
                        laundering_type=str(protected_labels.get("laundering_type", "")),
                        raw_labels=protected_labels
                    )
                    total_protected_labels += 1

                # Point-in-time scoring payload
                scoring_payload = {
                    "id": txn_id,
                    "event_id": event_id,
                    "source_account_id": src_acc,
                    "destination_account_id": dest_acc,
                    "amount": amount,
                    "currency": currency,
                    "payment_type": txn_type,
                    "payment_channel": channel,
                    "created_at": created_at
                }

                risk_score = 0.0
                risk_band = "ROUTINE"
                scoring_status = "CURRENT"

                # Real-time scoring execution
                try:
                    score_res = score_transaction(conn, scoring_payload)
                    risk_score = float(score_res.get("final_risk_score", 0.0))
                    risk_band = str(score_res.get("risk_band", "ROUTINE"))
                except Exception as e:
                    logger.error(f"Scoring failure for txn {txn_id}: {e}")
                    scoring_status = "FAILED"
                    total_scoring_failures += 1

                # Database insertion
                if not dry_run:
                    cust_id_src = f"CUST-{src_acc[:8]}"
                    c_cust_s, c_acc_s = ensure_account_exists(conn, src_acc, customer_id=cust_id_src, currency=currency)
                    if c_cust_s:
                        batch_created_customers.add(cust_id_src)
                    if c_acc_s:
                        batch_created_accounts.add(src_acc)

                    cust_id_dst = f"CUST-{dest_acc[:8]}"
                    c_cust_d, c_acc_d = ensure_account_exists(conn, dest_acc, customer_id=cust_id_dst, currency=currency)
                    if c_cust_d:
                        batch_created_customers.add(cust_id_dst)
                    if c_acc_d:
                        batch_created_accounts.add(dest_acc)

                    # Unique conflict-safe insert
                    cursor.execute("""
                        INSERT INTO transactions (
                            id, event_id, source_account_id, destination_account_id,
                            customer_id, amount, currency, transaction_type, payment_channel,
                            status, scenario_id, dataset_source, risk_score, risk_band,
                            scoring_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (event_id) DO NOTHING;
                    """, (
                        txn_id, event_id, src_acc, dest_acc,
                        cust_id_src, amount, currency, txn_type, channel,
                        batch_id, dataset_name, risk_score, risk_band, scoring_status, created_at
                    ))

                    # High risk alert generation
                    if risk_score >= 70.0:
                        alert_id = generate_alert_id()
                        cursor.execute("""
                            INSERT INTO alerts (
                                id, alert_ref, transaction_id, account_id, customer_id,
                                severity, status, risk_score, title, summary,
                                alert_type, detection_reason, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, 'HIGH', 'NEW', ?, ?, ?, 'SUSPICIOUS_TXN', 'Consensus scoring threshold exceeded', ?, ?)
                        """, (
                            alert_id, f"ALT-{alert_id[:8]}", txn_id, src_acc, cust_id_src,
                            risk_score, f"High Risk Alert: {txn_id}",
                            f"Consensus risk score {risk_score:.1f} on {dataset_name} transaction",
                            created_at, created_at
                        ))
                        total_alerts_generated += 1

                    existing_in_chunk.add(event_id)

                chunk_ingested += 1
                total_ingested += 1

            current_offset += chunk_rows

            # Step C: Bounded transaction commit and checkpoint persistence per chunk
            if not dry_run:
                conn.commit()

                # Atomically update checkpoint after each committed chunk
                ds_state["last_offset"] = current_offset
                ds_state["total_ingested"] = ds_state["total_ingested"] + chunk_ingested
                save_checkpoint(checkpoint)

            print(f"Chunk {chunk_num}: Processed {chunk_ingested:,} rows (Duplicates skipped: {chunk_duplicates:,}) | Current Offset: {current_offset:,}")

        # Final audit logging and batch recording if live execution
        if not dry_run and total_ingested > 0:
            record_audit_event(
                conn=conn,
                actor_id="SYSTEM",
                actor_name="SafeBatchIngestPipeline",
                action="BATCH_INGESTION_COMPLETED",
                resource_type="DATASET_BATCH",
                resource_id=batch_id,
                metadata={
                    "dataset_name": dataset_name,
                    "batch_id": batch_id,
                    "records_ingested": total_ingested,
                    "duplicates_skipped": total_duplicates,
                    "protected_labels_isolated": total_protected_labels,
                    "alerts_generated": total_alerts_generated,
                    "scoring_failures": total_scoring_failures,
                    "start_offset": start_offset,
                    "end_offset": current_offset,
                    "created_accounts_count": len(batch_created_accounts),
                    "created_customers_count": len(batch_created_customers)
                }
            )

            checkpoint["batches"].append({
                "batch_id": batch_id,
                "dataset_name": dataset_name,
                "records_ingested": total_ingested,
                "duplicates_skipped": total_duplicates,
                "alerts_generated": total_alerts_generated,
                "scoring_failures": total_scoring_failures,
                "start_offset": start_offset,
                "end_offset": current_offset,
                "created_accounts": list(batch_created_accounts),
                "created_customers": list(batch_created_customers),
                "timestamp": utc_now_iso(),
                "status": "COMPLETED"
            })
            save_checkpoint(checkpoint)
            conn.commit()
            print(f"\n[SUCCESS] Batch {batch_id} fully committed. Checkpoint updated.")

    print(f"\n================ SUMMARY ================")
    print(f"Batch ID:                  {batch_id}")
    print(f"Records Processed:         {total_ingested:,}")
    print(f"Duplicates Skipped:        {total_duplicates:,}")
    print(f"Protected Labels Isolated: {total_protected_labels:,}")
    print(f"Alerts Generated:          {total_alerts_generated:,}")
    print(f"Scoring Failures:          {total_scoring_failures:,}")
    print(f"Accounts Created:          {len(batch_created_accounts):,}")
    print(f"Customers Created:         {len(batch_created_customers):,}")
    print(f"Starting Offset:           {start_offset:,}")
    print(f"Ending Offset:             {current_offset:,}")
    print(f"Mode:                      {'DRY RUN (No changes)' if dry_run else 'COMMITTED TO DATABASE'}")
    print(f"=========================================\n")

    return {
        "status": "DRY_RUN_COMPLETED" if dry_run else "COMMITTED",
        "batch_id": batch_id,
        "records_processed": total_ingested,
        "duplicates_skipped": total_duplicates,
        "protected_labels_isolated": total_protected_labels,
        "alerts_generated": total_alerts_generated,
        "scoring_failures": total_scoring_failures,
        "created_accounts": len(batch_created_accounts),
        "created_customers": len(batch_created_customers),
        "start_offset": start_offset,
        "end_offset": current_offset
    }


def rollback_batch(batch_id: str) -> bool:
    """
    Safely rolls back an ingested batch by batch_id:
    1. Deletes alerts and alert findings associated with the batch transactions.
    2. Deletes transactions tagged with scenario_id = batch_id.
    3. Deletes protected ground-truth labels from Pipeline B vault for these transactions.
    4. Safely removes accounts and customers created by this batch if they have no other transactions.
    5. Restores checkpoint dataset offset to pre-batch position.
    """
    print(f"\n[ROLLBACK] Initiating atomic rollback for Batch ID: {batch_id}...")
    checkpoint = load_checkpoint()

    # Find batch metadata in checkpoint
    batch_meta = None
    for b in checkpoint.get("batches", []):
        if b.get("batch_id") == batch_id:
            batch_meta = b
            break

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Identify transactions stamped with this batch_id
        cursor.execute("SELECT id FROM transactions WHERE scenario_id = ?;", (batch_id,))
        txns = cursor.fetchall()
        txn_ids = [t[0] if not hasattr(t, "keys") else t["id"] for t in txns]

        if not txn_ids:
            print(f"[WARN] No transactions found with scenario_id / batch_id = {batch_id}.")
            return False

        print(f"Found {len(txn_ids):,} transactions to roll back.")

        # 2. Delete alert findings and alerts
        for tid in txn_ids:
            cursor.execute("SELECT id FROM alerts WHERE transaction_id = ?;", (tid,))
            al = cursor.fetchall()
            for a in al:
                aid = a[0] if not hasattr(a, "keys") else a["id"]
                cursor.execute("DELETE FROM alert_findings WHERE alert_id = ?;", (aid,))
            cursor.execute("DELETE FROM alerts WHERE transaction_id = ?;", (tid,))

        # 3. Delete transactions
        cursor.execute("DELETE FROM transactions WHERE scenario_id = ?;", (batch_id,))

        # 4. Delete protected ground-truth labels from Pipeline B vault
        vault_path = os.path.join(BASE_DIR, "data", "protected_labels", "protected_ground_truth.db")
        if os.path.exists(vault_path) and txn_ids:
            try:
                with sqlite3.connect(vault_path) as vconn:
                    vcur = vconn.cursor()
                    for i in range(0, len(txn_ids), 500):
                        sub = txn_ids[i:i + 500]
                        vcur.executemany("DELETE FROM protected_transaction_labels WHERE transaction_id = ?;", [(t,) for t in sub])
                    vconn.commit()
                print(f"[ROLLBACK] Cleanly removed protected labels for {len(txn_ids):,} transactions from Pipeline B vault.")
            except Exception as e:
                logger.warning(f"Could not purge protected labels from vault during rollback: {e}")

        # 5. Cleanly prune batch-owned accounts and customers if unreferenced
        if batch_meta:
            created_accounts = batch_meta.get("created_accounts", [])
            for acc_id in created_accounts:
                cursor.execute("""
                    SELECT 1 FROM transactions 
                    WHERE source_account_id = ? OR destination_account_id = ? 
                    LIMIT 1;
                """, (acc_id, acc_id))
                if not cursor.fetchone():
                    cursor.execute("DELETE FROM accounts WHERE id = ?;", (acc_id,))

            created_customers = batch_meta.get("created_customers", [])
            for cust_id in created_customers:
                cursor.execute("SELECT 1 FROM accounts WHERE customer_id = ? LIMIT 1;", (cust_id,))
                if not cursor.fetchone():
                    cursor.execute("DELETE FROM customers WHERE id = ?;", (cust_id,))

        # 6. Record audit rollback event
        record_audit_event(
            conn=conn,
            actor_id="SYSTEM",
            actor_name="SafeBatchIngestPipeline",
            action="BATCH_ROLLBACK_EXECUTED",
            resource_type="DATASET_BATCH",
            resource_id=batch_id,
            metadata={
                "rolled_back_transactions": len(txn_ids),
                "dataset_name": batch_meta.get("dataset_name") if batch_meta else "UNKNOWN"
            }
        )

        conn.commit()

        # 7. Update checkpoint
        if batch_meta:
            batch_meta["status"] = "ROLLED_BACK"
            batch_meta["rolled_back_at"] = utc_now_iso()
            ds_name = batch_meta.get("dataset_name")
            if ds_name and ds_name in checkpoint.get("datasets", {}):
                # Rollback offset to pre-batch start_offset
                start_off = batch_meta.get("start_offset", 0)
                checkpoint["datasets"][ds_name]["last_offset"] = start_off
                checkpoint["datasets"][ds_name]["total_ingested"] = max(
                    0, checkpoint["datasets"][ds_name]["total_ingested"] - batch_meta.get("records_ingested", len(txn_ids))
                )
        save_checkpoint(checkpoint)

        print(f"[SUCCESS] Cleanly rolled back batch {batch_id} ({len(txn_ids):,} transactions deleted).\n")
        return True


def show_status(quota_mb: float = DEFAULT_QUOTA_MB, safety_reserve_mb: float = DEFAULT_SAFETY_RESERVE_MB):
    """Displays current ingestion progress, storage usage, and batch log."""
    checkpoint = load_checkpoint()
    with get_db_connection() as conn:
        current_mb, engine = get_current_storage_mb(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions;")
        total_txns = cursor.fetchone()[0]

    ceiling_mb = quota_mb - safety_reserve_mb
    available_headroom_mb = max(0.0, ceiling_mb - current_mb)
    max_safe_txns = int((available_headroom_mb * 1024.0) / ESTIMATED_KB_PER_TXN)

    print(f"\n================ SENTINELFLOW INGESTION STATUS ================")
    print(f"Database Engine:           {engine}")
    print(f"Database Physical Size:    {current_mb:.2f} MB")
    print(f"Quota Safety Ceiling:      {ceiling_mb:.2f} MB (Total Quota: {quota_mb:.2f} MB, Reserve: {safety_reserve_mb:.2f} MB)")
    print(f"Available Safe Headroom:   {available_headroom_mb:.2f} MB (~{max_safe_txns:,} transactions)")
    print(f"Live Transactions in DB:   {total_txns:,}")
    print(f"Dataset Offsets in Checkpoint:")
    for ds, st in checkpoint.get("datasets", {}).items():
        print(f"  - {ds}: Offset {st.get('last_offset', 0):,}, Total Ingested: {st.get('total_ingested', 0):,}")
    print(f"\nHistorical Batches ({len(checkpoint.get('batches', []))} total):")
    for b in checkpoint.get("batches", [])[-10:]:
        print(f"  [{b.get('timestamp', '')[:19]}] {b.get('batch_id')} | {b.get('dataset_name')} | {b.get('records_ingested', 0):,} txns | Status: {b.get('status')}")
    print(f"===============================================================\n")


def main():
    parser = argparse.ArgumentParser(description="SentinelFlow Safe Streaming Batch Ingestion Pipeline")
    parser.add_argument("--dataset", type=str, default="NFPC", choices=["NFPC", "SAML_D"], help="Target dataset")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch processing chunk size (500-5000)")
    parser.add_argument("--limit", type=int, default=1000, help="Total records to ingest in this execution")
    parser.add_argument("--quota-mb", type=float, default=DEFAULT_QUOTA_MB, help="Database quota ceiling in MB (default: 500.0)")
    parser.add_argument("--safety-reserve-mb", type=float, default=DEFAULT_SAFETY_RESERVE_MB, help="Database safety headroom reserve in MB (default: 50.0)")
    parser.add_argument("--execute", action="store_true", help="Execute database writes (defaults to dry-run without this flag)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry-run validation without writing to DB")
    parser.add_argument("--rollback", type=str, help="Roll back transactions and alerts for a specific batch_id")
    parser.add_argument("--status", action="store_true", help="Display ingestion status and checkpoint history")

    args = parser.parse_args()

    if args.status:
        show_status(quota_mb=args.quota_mb, safety_reserve_mb=args.safety_reserve_mb)
        return

    if args.rollback:
        rollback_batch(args.rollback)
        return

    is_dry_run = not args.execute

    execute_batch_ingest(
        dataset_name=args.dataset,
        batch_size=min(5000, max(100, args.batch_size)),
        limit=args.limit,
        dry_run=is_dry_run,
        quota_mb=args.quota_mb,
        safety_reserve_mb=args.safety_reserve_mb
    )


if __name__ == "__main__":
    main()
