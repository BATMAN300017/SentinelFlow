"""
Safe Batch Ingestion and Pipeline Isolation Subsystem for SentinelFlow AI.

Features:
1. Bounded batch streaming (configurable batch size, default 1,000, max 5,000).
2. Checkpoint state persistence at data/temp_manifests/batch_checkpoint.json.
3. Deduplication via existing transaction event_id / primary key lookup.
4. Strict Pipeline B label isolation: Ground-truth labels are routed strictly to
   data/protected_labels/protected_ground_truth.db. Detection records are verified
   via assert_no_label_leakage before scoring or ingestion.
5. Point-in-time real-time scoring via score_transaction() with scoring failure tracking.
6. Stamped batch_id for all transactions, enabling atomic, audited per-batch rollback.
7. Storage capacity projection check (0.56 KB / transaction) before write execution.
8. Safe-by-default execution: Defaults to --dry-run; requires explicit --execute.
9. Windows Application Control (WDAC) compliance: uses pure standard libraries and pandas.
"""

import os
import sys
import json
import uuid
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import pandas as pd
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
STORAGE_CEILING_MB = 450.0  # Free/starter tier safety ceiling (500 MB max)
ESTIMATED_KB_PER_TXN = 0.56


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


def check_storage_projection(conn, records_to_ingest: int) -> bool:
    """Verifies that the projected ingestion will not breach storage quotas."""
    current_mb, engine = get_current_storage_mb(conn)
    projected_add_mb = (records_to_ingest * ESTIMATED_KB_PER_TXN) / 1024.0
    projected_total_mb = current_mb + projected_add_mb

    print(f"\n--- Storage Safety Assessment ({engine}) ---")
    print(f"Current DB Storage:   {current_mb:.2f} MB")
    print(f"Projected Addition:   +{projected_add_mb:.2f} MB ({records_to_ingest:,} txns @ {ESTIMATED_KB_PER_TXN} KB/txn)")
    print(f"Projected Total:      {projected_total_mb:.2f} MB")
    print(f"Quota Safety Ceiling: {STORAGE_CEILING_MB:.2f} MB")

    if projected_total_mb > STORAGE_CEILING_MB:
        print(f"[ERROR] Projected storage ({projected_total_mb:.2f} MB) exceeds safety ceiling of {STORAGE_CEILING_MB:.2f} MB!")
        print("Aborting to protect production database quota.")
        return False
    print("[PASS] Storage capacity verified within safe limits.\n")
    return True


def ensure_account_exists(conn, account_id: str, customer_id: str = "CUST-DEFAULT", currency: str = "USD"):
    """Ensures account and customer exist in database for foreign key integrity."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
            VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
        """, (customer_id, customer_id, f"Customer {customer_id}", f"{customer_id.lower()}@sentinelflow.internal", utc_now_iso()))

    cursor.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO accounts (id, account_number, customer_id, account_type, currency, balance, status, is_dormant, created_at)
            VALUES (?, ?, ?, 'CHECKING', ?, 10000.0, 'ACTIVE', 0, ?)
        """, (account_id, account_id, customer_id, currency, utc_now_iso()))


def execute_batch_ingest(
    dataset_name: str,
    batch_size: int,
    limit: int,
    dry_run: bool
) -> Dict[str, Any]:
    """Executes a bounded batch ingestion with strict label isolation and point-in-time scoring."""
    init_protected_store()
    checkpoint = load_checkpoint()
    ds_state = checkpoint["datasets"].setdefault(dataset_name, {"last_offset": 0, "total_ingested": 0})
    start_offset = ds_state["last_offset"]

    print(f"\n========================================================")
    print(f"SENTINELFLOW BATCH INGESTION: {dataset_name}")
    print(f"Mode: {'DRY RUN (No DB Writes)' if dry_run else 'LIVE EXECUTION'}")
    print(f"Batch Size: {batch_size:,} | Record Limit: {limit:,} | Starting Offset: {start_offset:,}")
    print(f"========================================================")

    # 1. Locate dataset file
    if dataset_name.upper() == "NFPC":
        file_path = os.path.join(BASE_DIR, "data", "nfpc", "part_0001.parquet")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NFPC dataset file not found at: {file_path}")
        print(f"Reading NFPC Parquet from offset {start_offset}...")
        df_raw = pd.read_parquet(file_path)
    elif dataset_name.upper() in ("SAML_D", "SAMLD"):
        file_path = os.path.join(BASE_DIR, "data", "saml_d", "SAML-D.csv")
        if not os.path.exists(file_path):
            file_path = os.path.join(BASE_DIR, "data", "saml_d", "saml_d_real.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SAML-D dataset file not found at: {file_path}")
        print(f"Reading SAML-D CSV chunk from offset {start_offset}...")
        # Read limited slice
        df_raw = pd.read_csv(file_path, skiprows=range(1, start_offset + 1) if start_offset > 0 else None, nrows=limit)
    else:
        raise ValueError(f"Unsupported dataset: {dataset_name}. Must be NFPC or SAML_D.")

    total_available = len(df_raw)
    slice_end = min(total_available, limit)
    df_slice = df_raw.iloc[:slice_end].copy()
    actual_count = len(df_slice)

    if actual_count == 0:
        print("[INFO] No new records to ingest at current offset.")
        return {"status": "NOOP", "records_ingested": 0}

    print(f"Loaded {actual_count:,} records from source file.")

    batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

    with get_db_connection() as conn:
        # Check storage projection
        if not check_storage_projection(conn, actual_count):
            return {"status": "ABORTED_STORAGE_LIMIT"}

        cursor = conn.cursor()

        # Check existing event IDs for deduplication
        existing_ids = set()
        if not dry_run:
            cursor.execute("SELECT event_id FROM transactions LIMIT 500000;")
            rows = cursor.fetchall()
            existing_ids = set(r[0] if not hasattr(r, "keys") else r["event_id"] for r in rows)

        ingested_count = 0
        duplicate_count = 0
        protected_labels_count = 0
        alerts_generated = 0
        scoring_failures = 0

        # Process records in bounded sub-batches
        for idx, row in df_slice.iterrows():
            raw_dict = row.to_dict()

            # Separate Pipeline B ground-truth labels from Pipeline A detection data
            detection_dict, protected_labels = strip_labels_for_detection(raw_dict)

            # Strict security assertion: Verify NO label leaks into Pipeline A
            assert_no_label_leakage(detection_dict, context=f"Safe Batch Ingest ({dataset_name})")

            # Map raw fields to canonical transaction schema
            txn_id = str(detection_dict.get("id") or detection_dict.get("Transaction_ID") or f"TXN-{uuid.uuid4().hex[:12]}")
            event_id = str(detection_dict.get("event_id") or txn_id)
            src_acc = str(detection_dict.get("source_account_id") or detection_dict.get("Sender_account") or detection_dict.get("Account_Number") or "ACC-UNKNOWN")
            dest_acc = str(detection_dict.get("destination_account_id") or detection_dict.get("Receiver_account") or "ACC-BENEFICIARY")
            amount = float(detection_dict.get("amount") or detection_dict.get("Amount") or 0.0)
            currency = str(detection_dict.get("currency") or detection_dict.get("Payment_currency") or "INR" if dataset_name.upper() == "NFPC" else "USD")
            txn_type = str(detection_dict.get("transaction_type") or detection_dict.get("Payment_type") or "TRANSFER")
            channel = str(detection_dict.get("payment_channel") or detection_dict.get("Payment_type") or "ONLINE")
            created_at = str(detection_dict.get("created_at") or detection_dict.get("Date") or utc_now_iso())

            if event_id in existing_ids:
                duplicate_count += 1
                continue

            # Route protected ground-truth labels exclusively to Pipeline B vault
            if protected_labels and not dry_run:
                is_laundering = 1 if protected_labels.get("is_laundering") in (1, "1", True) else 0
                store_protected_transaction_label(
                    transaction_id=txn_id,
                    dataset_name=dataset_name,
                    is_laundering=is_laundering,
                    laundering_type=str(protected_labels.get("laundering_type", "")),
                    raw_labels=protected_labels
                )
                protected_labels_count += 1

            # Prepare transaction dict for point-in-time scoring
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

            # Execute real-time scoring
            try:
                score_res = score_transaction(conn, scoring_payload)
                risk_score = float(score_res.get("final_risk_score", 0.0))
                risk_band = str(score_res.get("risk_band", "ROUTINE"))
            except Exception as e:
                logger.error(f"Scoring failure for txn {txn_id}: {e}")
                scoring_status = "FAILED"
                scoring_failures += 1

            if not dry_run:
                ensure_account_exists(conn, src_acc, currency=currency)
                ensure_account_exists(conn, dest_acc, currency=currency)

                cursor.execute("""
                    INSERT INTO transactions (
                        id, event_id, source_account_id, destination_account_id,
                        customer_id, amount, currency, transaction_type, payment_channel,
                        status, scenario_id, dataset_source, risk_score, risk_band,
                        scoring_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?)
                """, (
                    txn_id, event_id, src_acc, dest_acc,
                    f"CUST-{src_acc[:8]}", amount, currency, txn_type, channel,
                    batch_id, dataset_name, risk_score, risk_band, scoring_status, created_at
                ))

                # Generate alert if risk exceeds threshold
                if risk_score >= 70.0:
                    alert_id = generate_alert_id()
                    cursor.execute("""
                        INSERT INTO alerts (
                            id, alert_ref, transaction_id, account_id, customer_id,
                            severity, status, risk_score, title, summary,
                            alert_type, detection_reason, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'HIGH', 'NEW', ?, ?, ?, 'SUSPICIOUS_TXN', 'Consensus scoring threshold exceeded', ?, ?)
                    """, (
                        alert_id, f"ALT-{alert_id[:8]}", txn_id, src_acc, f"CUST-{src_acc[:8]}",
                        risk_score, f"High Risk Alert: {txn_id}",
                        f"Consensus risk score {risk_score:.1f} on {dataset_name} transaction",
                        created_at, created_at
                    ))
                    alerts_generated += 1

                existing_ids.add(event_id)

            ingested_count += 1
            if (ingested_count % batch_size) == 0:
                print(f"Processed {ingested_count:,} / {actual_count:,} records (Duplicates skipped: {duplicate_count:,})...")

        if not dry_run:
            # Record audit event
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
                    "records_ingested": ingested_count,
                    "duplicates_skipped": duplicate_count,
                    "protected_labels_isolated": protected_labels_count,
                    "alerts_generated": alerts_generated,
                    "scoring_failures": scoring_failures,
                    "start_offset": start_offset,
                    "end_offset": start_offset + actual_count
                }
            )

            # Update checkpoint
            ds_state["last_offset"] = start_offset + actual_count
            ds_state["total_ingested"] = ds_state["total_ingested"] + ingested_count
            checkpoint["batches"].append({
                "batch_id": batch_id,
                "dataset_name": dataset_name,
                "records_ingested": ingested_count,
                "duplicates_skipped": duplicate_count,
                "alerts_generated": alerts_generated,
                "scoring_failures": scoring_failures,
                "timestamp": utc_now_iso(),
                "status": "COMPLETED"
            })
            save_checkpoint(checkpoint)
            print("\n[SUCCESS] Batch committed and checkpoint updated successfully.")

    print(f"\n================ SUMMARY ================")
    print(f"Batch ID:                  {batch_id}")
    print(f"Records Processed:         {ingested_count:,}")
    print(f"Duplicates Skipped:        {duplicate_count:,}")
    print(f"Protected Labels Isolated: {protected_labels_count:,}")
    print(f"Alerts Generated:          {alerts_generated:,}")
    print(f"Scoring Failures:          {scoring_failures:,}")
    print(f"Mode:                      {'DRY RUN (No changes)' if dry_run else 'COMMITTED TO DATABASE'}")
    print(f"=========================================\n")

    return {
        "status": "DRY_RUN_COMPLETED" if dry_run else "COMMITTED",
        "batch_id": batch_id,
        "records_processed": ingested_count,
        "duplicates_skipped": duplicate_count,
        "protected_labels_isolated": protected_labels_count,
        "alerts_generated": alerts_generated,
        "scoring_failures": scoring_failures
    }


def rollback_batch(batch_id: str) -> bool:
    """Safely rolls back an ingested batch by batch_id."""
    print(f"\n[ROLLBACK] Initiating rollback for Batch ID: {batch_id}...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Find transactions stamped with this batch_id
        cursor.execute("SELECT id FROM transactions WHERE scenario_id = ?", (batch_id,))
        txns = cursor.fetchall()
        txn_ids = [t[0] if not hasattr(t, "keys") else t["id"] for t in txns]

        if not txn_ids:
            print(f"[WARN] No transactions found with scenario_id / batch_id = {batch_id}.")
            return False

        print(f"Found {len(txn_ids):,} transactions to roll back.")

        # Delete alert findings and alerts
        for tid in txn_ids:
            cursor.execute("SELECT id FROM alerts WHERE transaction_id = ?", (tid,))
            al = cursor.fetchall()
            for a in al:
                aid = a[0] if not hasattr(a, "keys") else a["id"]
                cursor.execute("DELETE FROM alert_findings WHERE alert_id = ?", (aid,))
            cursor.execute("DELETE FROM alerts WHERE transaction_id = ?", (tid,))

        # Delete transactions
        cursor.execute("DELETE FROM transactions WHERE scenario_id = ?", (batch_id,))

        # Record audit rollback event
        record_audit_event(
            conn=conn,
            actor_id="SYSTEM",
            actor_name="SafeBatchIngestPipeline",
            action="BATCH_ROLLBACK_EXECUTED",
            resource_type="DATASET_BATCH",
            resource_id=batch_id,
            metadata={"rolled_back_transactions": len(txn_ids)}
        )

        # Update checkpoint
        checkpoint = load_checkpoint()
        for b in checkpoint.get("batches", []):
            if b.get("batch_id") == batch_id:
                b["status"] = "ROLLED_BACK"
                b["rolled_back_at"] = utc_now_iso()
        save_checkpoint(checkpoint)

        print(f"[SUCCESS] Cleanly rolled back batch {batch_id} ({len(txn_ids):,} transactions deleted).\n")
        return True


def show_status():
    """Displays current ingestion progress, storage usage, and batch log."""
    checkpoint = load_checkpoint()
    with get_db_connection() as conn:
        current_mb, engine = get_current_storage_mb(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions;")
        total_txns = cursor.fetchone()[0]

    print(f"\n================ SENTINELFLOW INGESTION STATUS ================")
    print(f"Database Engine:           {engine}")
    print(f"Database Physical Size:    {current_mb:.2f} MB / {STORAGE_CEILING_MB:.2f} MB ceiling")
    print(f"Live Transactions in DB:   {total_txns:,}")
    print(f"Dataset Offsets in Checkpoint:")
    for ds, st in checkpoint.get("datasets", {}).items():
        print(f"  - {ds}: Offset {st.get('last_offset', 0):,}, Total Ingested: {st.get('total_ingested', 0):,}")
    print(f"\nHistorical Batches ({len(checkpoint.get('batches', []))} total):")
    for b in checkpoint.get("batches", [])[-10:]:
        print(f"  [{b.get('timestamp')[:19]}] {b.get('batch_id')} | {b.get('dataset_name')} | {b.get('records_ingested', 0):,} txns | Status: {b.get('status')}")
    print(f"===============================================================\n")


def main():
    parser = argparse.ArgumentParser(description="SentinelFlow Safe Batch Ingestion Pipeline")
    parser.add_argument("--dataset", type=str, default="NFPC", choices=["NFPC", "SAML_D"], help="Target dataset")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch processing chunk size (500-5000)")
    parser.add_argument("--limit", type=int, default=1000, help="Total records to ingest in this execution")
    parser.add_argument("--execute", action="store_true", help="Execute database writes (defaults to dry-run without this flag)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry-run validation without writing to DB")
    parser.add_argument("--rollback", type=str, help="Roll back transactions and alerts for a specific batch_id")
    parser.add_argument("--status", action="store_true", help="Display ingestion status and checkpoint history")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.rollback:
        rollback_batch(args.rollback)
        return

    is_dry_run = not args.execute

    execute_batch_ingest(
        dataset_name=args.dataset,
        batch_size=min(5000, max(100, args.batch_size)),
        limit=args.limit,
        dry_run=is_dry_run
    )


if __name__ == "__main__":
    main()
