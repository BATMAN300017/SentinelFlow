"""
Seeds SentinelFlow AI database with:
- DATASET 1: SAML-D (Synthetic Transaction Monitoring Dataset for AML)
  Populates:
  - Live transactions stream from real SAML-D CSV records
  - Protected ground truth store for evaluation and retraining
- DATASET 2: NFPC Mule Account / Labeled Dataset
  Populates:
  - Real Indian banking transactions from NFPC Parquet partition
  - Protected ground truth store for evaluation and retraining

STRICT ARCHITECTURAL SEPARATION:
- Real dataset ingestion NEVER creates demo alerts, demo investigations,
  fictional evidence, or simulated analyst decisions.
- Optional demo fixture generation is strictly isolated in `seed_demo_fixtures_from_scored_txns`
  and requires explicit invocation plus environment authorization.
- Real transactions are scored strictly through the operational detection engine.
- A scoring engine failure sets `risk_score = NULL` and `risk_band = 'FAILED'`.
"""

import os
import sys
import argparse
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import init_db, transaction_scope, get_db_connection
from app.core.security import hash_password
from app.core.guards import check_demo_environment_guard
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.label_isolation import (
    store_protected_transaction_label,
    store_protected_account_label,
    init_protected_store
)
from app.detection.engine import score_transaction
from app.core.logging import logger


def ingest_real_saml_and_nfpc_datasets(
    conn=None,
    saml_limit: int = 5000,
    nfpc_limit: int = 5000,
    score_txns: bool = True,
    purge_existing: bool = True
) -> Dict[str, Any]:
    """
    Ingests real SAML-D and NFPC datasets into the application database.
    Strictly performs real data ingestion and label isolation:
    - Never creates demo alerts, demo investigations, or fictional evidence.
    - Never treats ground truth labels as operational analyst decisions.
    - Transaction risk scores derive purely from operational detection engine.
    - Scoring failure sets risk_score = NULL and risk_band = 'FAILED'.
    """
    now = datetime.now(timezone.utc)

    def _execute_ingest(c):
        cursor = c.cursor()

        # 1. Purge existing records if requested
        if purge_existing:
            logger.info("Purging existing application records...")
            cursor.execute("PRAGMA foreign_keys = OFF;")
            cursor.execute("DELETE FROM investigation_events")
            cursor.execute("DELETE FROM analyst_feedback")
            cursor.execute("DELETE FROM investigation_tasks")
            cursor.execute("DELETE FROM investigation_notes")
            cursor.execute("DELETE FROM evidence_items")
            cursor.execute("DELETE FROM investigation_alerts")
            cursor.execute("DELETE FROM alert_findings")
            cursor.execute("DELETE FROM alerts")
            cursor.execute("DELETE FROM investigations")
            cursor.execute("DELETE FROM transactions")
            cursor.execute("DELETE FROM accounts")
            cursor.execute("DELETE FROM customers")
            cursor.execute("PRAGMA foreign_keys = ON;")

        # 2. Seed Base System Users
        users = [
            ("USR-INV-01", "sarah_investigator", "sarah.lin@sentinelflow.bank", "Sarah Lin", "investigator"),
            ("USR-SR-02", "marcus_senior", "marcus.vance@sentinelflow.bank", "Marcus Vance", "senior_investigator"),
            ("USR-ADM-03", "elena_admin", "elena.rostova@sentinelflow.bank", "Elena Rostova", "fraud_admin"),
            ("USR-AUD-04", "arthur_auditor", "arthur.pendelton@sentinelflow.bank", "Arthur Pendelton", "auditor"),
            ("SYSTEM_COPILOT", "system_copilot", "copilot@sentinelflow.bank", "SentinelFlow AI Copilot", "investigator")
        ]
        pwd_hash = hash_password("password123")
        for u_id, uname, email, fname, role in users:
            cursor.execute("""
                INSERT OR REPLACE INTO users (id, username, email, full_name, role, hashed_password, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (u_id, uname, email, fname, role, pwd_hash, (now - timedelta(days=90)).isoformat()))

        data_dir = os.path.join(BASE_DIR, "data")
        saml_csv_path = os.path.join(data_dir, "saml_d", "saml_d_real.csv")
        nfpc_parquet_path = os.path.join(data_dir, "nfpc", "part_0001.parquet")

        # Ingest SAML-D if file exists
        total_saml_ingested = 0
        total_saml_labels_isolated = 0

        if os.path.exists(saml_csv_path):
            saml_adapter = SamlDAdapter(batch_size=1000)
            for raw_batch in saml_adapter.load_batches(saml_csv_path, max_records=saml_limit):
                normalized_batch, batch_res = saml_adapter.process_and_isolate(raw_batch, f"BATCH-SAML-INIT-{total_saml_ingested}")
                total_saml_labels_isolated += batch_res.labels_isolated

                for txn in normalized_batch:
                    src = txn["source_account_id"]
                    dest = txn.get("destination_account_id")
                    ts = txn["created_at"]
                    curr = txn["currency"]
                    amt = txn["amount"]

                    cursor.execute("""
                        INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                        VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                    """, (f"CUST-{src}", f"REF-{src}", f"SAML Entity {src[-4:]}", f"holder_{src[-4:]}@saml-bank.com", ts))

                    cursor.execute("""
                        INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (src, src, f"CUST-{src}", curr, round(amt * 1.5, 2), ts))

                    if dest:
                        cursor.execute("""
                            INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                            VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                        """, (f"CUST-{dest}", f"REF-{dest}", f"SAML Counterparty {dest[-4:]}", f"counterparty_{dest[-4:]}@saml-bank.com", ts))

                        cursor.execute("""
                            INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (dest, dest, f"CUST-{dest}", curr, round(amt * 0.8, 2), ts))

                    cursor.execute("""
                        INSERT OR REPLACE INTO transactions (
                            id, event_id, source_account_id, destination_account_id, customer_id,
                            amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'PENDING', 'SAML_D', ?)
                    """, (
                        txn["id"], txn["event_id"], src, dest, f"CUST-{src}",
                        amt, curr, txn.get("payment_type", "TRANSFER"),
                        txn.get("payment_channel", "WIRE"), "COMPLETED", ts
                    ))
                    total_saml_ingested += 1

                    if score_txns:
                        try:
                            scoring_res = score_transaction(c, {
                                "id": txn["id"],
                                "event_id": txn["event_id"],
                                "source_account_id": src,
                                "destination_account_id": dest,
                                "customer_id": f"CUST-{src}",
                                "amount": amt,
                                "currency": curr,
                                "transaction_type": txn.get("payment_type", "TRANSFER"),
                                "payment_channel": txn.get("payment_channel", "WIRE"),
                                "status": "COMPLETED",
                                "created_at": ts
                            })
                            final_score = scoring_res.get("final_risk_score") if scoring_res else None
                            if final_score is not None:
                                final_band = scoring_res.get("risk_band", "ROUTINE")
                                cursor.execute("UPDATE transactions SET risk_score = ?, risk_band = ?, scoring_status = 'CURRENT' WHERE id = ?", (float(final_score), final_band, txn["id"]))
                            else:
                                cursor.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED', scoring_status = 'UNAVAILABLE' WHERE id = ?", (txn["id"],))
                        except Exception as e:
                            logger.warning(f"SAML transaction scoring exception on {txn['id']}: {e}")
                            cursor.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED', scoring_status = 'UNAVAILABLE' WHERE id = ?", (txn["id"],))

        # Ingest NFPC if file exists
        total_nfpc_ingested = 0
        total_nfpc_labels_isolated = 0

        if os.path.exists(nfpc_parquet_path):
            nfpc_adapter = NfpcAdapter(batch_size=1000)
            for raw_batch in nfpc_adapter.load_batches(nfpc_parquet_path, max_records=nfpc_limit):
                normalized_batch, batch_res = nfpc_adapter.process_and_isolate(raw_batch, f"BATCH-NFPC-INIT-{total_nfpc_ingested}")
                total_nfpc_labels_isolated += batch_res.labels_isolated

                for txn in normalized_batch:
                    src = txn["source_account_id"]
                    dest = txn.get("destination_account_id")
                    ts = txn["created_at"]
                    curr = txn["currency"]
                    amt = txn["amount"]

                    cursor.execute("""
                        INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                        VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                    """, (f"CUST-{src}", f"REF-{src}", f"Indian Banking Customer {src[-4:]}", f"holder_{src[-4:]}@indian-bank.in", ts))

                    cursor.execute("""
                        INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (src, src, f"CUST-{src}", curr, 50000.0, ts))

                    if dest:
                        cursor.execute("""
                            INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                            VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                        """, (f"CUST-{dest}", f"REF-{dest}", f"Counterparty {dest[-4:]}", f"cp_{dest[-4:]}@indian-bank.in", ts))

                        cursor.execute("""
                            INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (dest, dest, f"CUST-{dest}", curr, 25000.0, ts))

                    cursor.execute("""
                        INSERT OR REPLACE INTO transactions (
                            id, event_id, source_account_id, destination_account_id, customer_id,
                            amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'PENDING', 'NFPC_MULE', ?)
                    """, (
                        txn["id"], txn["event_id"], src, dest, f"CUST-{src}",
                        amt, curr, txn.get("payment_type", "TRANSFER"),
                        txn.get("payment_channel", "IMPS"), "COMPLETED", ts
                    ))
                    total_nfpc_ingested += 1

                    if score_txns:
                        try:
                            scoring_res = score_transaction(c, {
                                "id": txn["id"],
                                "event_id": txn["event_id"],
                                "source_account_id": src,
                                "destination_account_id": dest,
                                "customer_id": f"CUST-{src}",
                                "amount": amt,
                                "currency": curr,
                                "transaction_type": txn.get("payment_type", "TRANSFER"),
                                "payment_channel": txn.get("payment_channel", "IMPS"),
                                "status": "COMPLETED",
                                "created_at": ts
                            })
                            final_score = scoring_res.get("final_risk_score") if scoring_res else None
                            if final_score is not None:
                                final_band = scoring_res.get("risk_band", "ROUTINE")
                                cursor.execute("UPDATE transactions SET risk_score = ?, risk_band = ? WHERE id = ?", (float(final_score), final_band, txn["id"]))
                            else:
                                cursor.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED', scoring_status = 'UNAVAILABLE' WHERE id = ?", (txn["id"],))
                        except Exception as e:
                            logger.warning(f"NFPC transaction scoring exception on {txn['id']}: {e}")
                            cursor.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED', scoring_status = 'UNAVAILABLE' WHERE id = ?", (txn["id"],))

        return {
            "total_saml_ingested": total_saml_ingested,
            "total_saml_labels_isolated": total_saml_labels_isolated,
            "total_nfpc_ingested": total_nfpc_ingested,
            "total_nfpc_labels_isolated": total_nfpc_labels_isolated
        }

    if conn is not None:
        return _execute_ingest(conn)
    else:
        with transaction_scope() as c:
            return _execute_ingest(c)


def seed_demo_fixtures_from_scored_txns(conn=None, max_alerts: int = 40) -> Dict[str, Any]:
    """
    Explicit, separate demo fixture generation path.
    Requires environment authorization via check_demo_environment_guard().
    Queries genuine scored transactions and instantiates demo alerts/investigations.
    If no eligible scored transactions exist, skips fixture generation cleanly without error.
    """
    check_demo_environment_guard("Demo fixture generation")

    def _execute_demo_seed(c):
        cursor = c.cursor()

        # Query eligible scored transactions (risk_score >= 65.0)
        cursor.execute("""
            SELECT id, source_account_id, customer_id, amount, currency, risk_score, risk_band, created_at
            FROM transactions
            WHERE risk_score IS NOT NULL
              AND risk_score >= 65.0
              AND (dataset_source != 'DEMO_FIXTURE')
            ORDER BY risk_score DESC
            LIMIT ?
        """, (max_alerts,))
        eligible_txns = cursor.fetchall()

        if not eligible_txns:
            logger.info("No eligible scored transactions found with risk_score >= 65.0. Skipping demo fixture generation.")
            return {
                "created_alerts": 0,
                "created_investigations": 0,
                "status": "SKIPPED_NO_SCORED_TRANSACTIONS",
                "message": "No eligible scored transactions with risk_score >= 65.0 found. Skipped demo fixture generation cleanly."
            }

        created_alerts: List[tuple] = []
        for i, t in enumerate(eligible_txns):
            t_id, src, cust, amt, curr, r_score, r_band, ts = t
            aid = f"ALT-DEMO-{1000 + i}"
            ref = f"ALT-2026-DEMO-{100 + i}"
            sev = "CRITICAL" if r_score >= 80.0 else ("HIGH" if r_score >= 68.0 else "MEDIUM")
            status = "CONVERTED_TO_INVESTIGATION" if i < 12 else ("TRIAGED" if i < 24 else "NEW")

            cursor.execute("""
                INSERT OR REPLACE INTO alerts (
                    id, alert_ref, transaction_id, account_id, customer_id,
                    severity, status, risk_score, title, summary, is_demo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                aid, ref, t_id, src, cust, sev, status, r_score,
                f"[DEMO FIXTURE] Pattern Signal: {curr} {amt:,.2f} Anomalous Velocity",
                f"[DEMO FIXTURE] Demonstration alert generated from high-risk transaction {t_id}.",
                ts, ts
            ))
            created_alerts.append((aid, ref, t))

            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'DEMO_FIXTURE', 'DEMO_TOPOLOGY_SIGNAL', '[DEMO FIXTURE] Simulated pattern node for demonstration', 35.0, 'v1.0', ?)
            """, (f"FND-{aid}-1", aid, ts))

        if not created_alerts:
            return {
                "created_alerts": 0,
                "created_investigations": 0,
                "status": "SKIPPED_NO_ALERTS",
                "message": "Zero alerts generated from scored transactions."
            }

        # Instantiate demo investigations linked safely to created alerts
        inv_cases = [
            ("CASE-2026-001", "[DEMO FIXTURE] Cross-Border Layering Dossier", "CRITICAL", "NEW", 94.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-002", "[DEMO FIXTURE] Rapid Dispersal Cluster Dossier", "HIGH", "IN_PROGRESS", 86.5, "SUSPICIOUS_UNCONFIRMED"),
            ("CASE-2026-003", "[DEMO FIXTURE] Circular Round-Tripping Ring", "HIGH", "PENDING_PEER_REVIEW", 82.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-004", "[DEMO FIXTURE] Commercial Remittance Lookalike", "MEDIUM", "RESOLVED", 54.0, "LEGITIMATE_ACTIVITY"),
            ("CASE-2026-005", "[DEMO FIXTURE] Rapid Pass-Through Dossier", "CRITICAL", "IN_PROGRESS", 91.0, None),
            ("CASE-2026-006", "[DEMO FIXTURE] High-Value Currency Conversion Spike", "HIGH", "TRIAGED", 79.5, None)
        ]

        created_investigations = 0
        n_alerts = len(created_alerts)

        for idx, (c_num, c_title, c_prio, c_status, c_score, c_disp) in enumerate(inv_cases):
            inv_id = f"INV-CASE-{idx+1:03d}"
            target_alert = created_alerts[idx % n_alerts]
            a_id, a_ref, a_txn = target_alert
            t_id, src, cust, amt, curr, r_score, r_band, ts = a_txn

            cursor.execute("""
                INSERT OR REPLACE INTO investigations (
                    id, case_number, title, summary, priority, status,
                    assigned_investigator_id, disposition, disposition_rationale,
                    evidence_completeness_score, model_version, rule_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'USR-INV-01', ?, ?, ?, 'v1.0', 'v1.0', ?, ?)
            """, (
                inv_id, c_num, c_title,
                f"Demo investigation dossier instantiated from alert {a_ref} on Account {src}.",
                c_prio, c_status, c_disp,
                "Demonstration case disposition rationale." if c_disp else None,
                85.0 if idx < 4 else 50.0,
                ts, ts
            ))

            cursor.execute("""
                INSERT OR IGNORE INTO investigation_alerts (investigation_id, alert_id, added_at)
                VALUES (?, ?, ?)
            """, (inv_id, a_id, ts))

            # Demo Evidence Items
            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, source_record_id, description,
                    observed_facts_json, verification_status, collector, created_at
                ) VALUES (?, ?, 'TRANSACTION', ?, ?, '{"is_demo_fixture": true}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-1", inv_id, t_id, f"[DEMO FIXTURE] Transfer of {curr} {amt:,.2f} on Account {src}", ts))

            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, description, is_completed, created_at)
                VALUES (?, ?, 'Inspect counterparty credentials', 'Verify counterparty licensing and country risk profile', 1, ?)
            """, (f"TSK-{inv_id}-1", inv_id, ts))

            cursor.execute("""
                INSERT OR REPLACE INTO investigation_notes (id, investigation_id, author_id, content, is_confidential, created_at)
                VALUES (?, ?, 'SYSTEM_COPILOT', ?, 0, ?)
            """, (
                f"NOT-{inv_id}-1", inv_id,
                f"Copilot Auto-Triage: Case {c_num} analyzed using multi-hop graph topology.",
                ts
            ))
            created_investigations += 1

        return {
            "created_alerts": len(created_alerts),
            "created_investigations": created_investigations,
            "status": "SUCCESS"
        }

    if conn is not None:
        return _execute_demo_seed(conn)
    else:
        with transaction_scope() as c:
            return _execute_demo_seed(c)


def seed_saml_and_nfpc_database(
    saml_limit: int = 5000,
    nfpc_limit: int = 5000,
    create_demo_fixtures: bool = False,
    purge_existing: bool = True,
    conn=None
) -> Dict[str, Any]:
    """
    Main entry point for real SAML-D & NFPC dataset seeding.
    By default, real ingestion ONLY is performed (create_demo_fixtures=False).
    Demo fixtures are generated ONLY if explicitly requested and environment permits.
    """
    init_db()
    init_protected_store()

    data_dir = os.path.join(BASE_DIR, "data")
    saml_csv_path = os.path.join(data_dir, "saml_d", "saml_d_real.csv")
    nfpc_parquet_path = os.path.join(data_dir, "nfpc", "part_0001.parquet")

    # If real files don't exist yet, run downloader
    if not os.path.exists(saml_csv_path) or not os.path.exists(nfpc_parquet_path):
        logger.info("Real dataset files missing; running download_real_datasets...")
        try:
            from scripts.download_real_datasets import main as run_download
            run_download()
        except Exception as e:
            logger.warning(f"Could not automatically download datasets: {e}")

    ingest_result = ingest_real_saml_and_nfpc_datasets(
        conn=conn,
        saml_limit=saml_limit,
        nfpc_limit=nfpc_limit,
        score_txns=True,
        purge_existing=purge_existing
    )

    demo_result = None
    if create_demo_fixtures:
        demo_result = seed_demo_fixtures_from_scored_txns(conn=conn)

    return {
        "ingest_result": ingest_result,
        "demo_result": demo_result
    }


def main():
    parser = argparse.ArgumentParser(description="SentinelFlow AI SAML-D and NFPC Dataset Ingestion")
    parser.add_argument("--saml-limit", type=int, default=5000, help="Max SAML-D transactions to ingest")
    parser.add_argument("--nfpc-limit", type=int, default=5000, help="Max NFPC transactions to ingest")
    parser.add_argument("--seed-demo", action="store_true", default=False, help="Explicitly enable demo alert & investigation fixtures")
    parser.add_argument("--no-purge", action="store_true", default=False, help="Do not purge existing records before ingestion")
    args = parser.parse_args()

    print("=" * 60)
    print("Initializing SentinelFlow AI database with REAL SAML-D & NFPC datasets...")
    print(f"  Demo Fixtures Enabled: {args.seed_demo}")
    print("=" * 60)

    res = seed_saml_and_nfpc_database(
        saml_limit=args.saml_limit,
        nfpc_limit=args.nfpc_limit,
        create_demo_fixtures=args.seed_demo,
        purge_existing=not args.no_purge
    )
    print(f"Seeding completed successfully: {res}")


if __name__ == "__main__":
    main()
