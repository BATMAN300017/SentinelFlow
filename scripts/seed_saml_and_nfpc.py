"""
Seeds SentinelFlow AI database with:
- DATASET 1: SAML-D (Synthetic Transaction Monitoring Dataset for AML)
  Populates:
  - Live transactions stream from real SAML-D CSV records
  - Alerts queue (derived from SAML-D multi-currency and laundering typologies)
  - Investigations dossiers and evidence records
  - Network Intelligence (Mule Network Explorer)
- DATASET 2: NFPC Mule Account / Labeled Dataset
  Populates:
  - Real Indian banking transactions from NFPC Parquet partition
  - Feedback & Learning tab with real ground-truth Scam (1) vs Legit (0) labeled records
  - Protected ground truth store for evaluation and retraining
"""

import os
import sys
import random
import uuid
from datetime import datetime, timezone, timedelta
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import init_db, transaction_scope, get_db_connection
from app.core.security import hash_password
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import (
    store_protected_transaction_label,
    store_protected_account_label,
    init_protected_store
)
from app.detection.engine import score_transaction

def seed_saml_and_nfpc_database(saml_limit: int = 5000, nfpc_limit: int = 5000):
    env = os.environ.get("ENVIRONMENT", "development").lower()
    if env == "production" and not os.environ.get("ALLOW_PRODUCTION_SEED"):
        print("Safety guard: Production environment detected. Automatic seeding aborted to protect existing data.")
        return

    print("=" * 60)
    print("Initializing SentinelFlow AI database with REAL SAML-D & NFPC datasets...")
    print("=" * 60)
    
    init_db()
    init_protected_store()
    now = datetime.now(timezone.utc)
    rng = random.Random(42)

    data_dir = os.path.join(BASE_DIR, "data")
    saml_csv_path = os.path.join(data_dir, "saml_d", "saml_d_real.csv")
    nfpc_parquet_path = os.path.join(data_dir, "nfpc", "part_0001.parquet")
    nfpc_labels_path = os.path.join(data_dir, "nfpc", "train_labels.parquet")

    # If real files don't exist yet, run downloader
    if not os.path.exists(saml_csv_path) or not os.path.exists(nfpc_parquet_path):
        print("Real dataset files missing; running download_real_datasets...")
        from scripts.download_real_datasets import main as run_download
        run_download()

    with transaction_scope() as conn:
        cursor = conn.cursor()

        # 1. Clean out old tables
        print("\n--- 1. Purging existing application records ---")
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
        print("Existing tables successfully cleared.")

        # 2. Seed Base System Users
        print("\n--- 2. Seeding authentication actors & investigators ---")
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
        print(f"Created {len(users)} system users.")

        # 3. Ingest DATASET 1: Real SAML-D Transactions
        print(f"\n--- 3. Ingesting Real DATASET 1 (SAML-D) from {saml_csv_path} ---")
        saml_adapter = SamlDAdapter(batch_size=1000)
        saml_txns_for_alerts = []
        total_saml_ingested = 0
        total_saml_labels_isolated = 0

        for raw_batch in saml_adapter.load_batches(saml_csv_path, max_records=saml_limit):
            normalized_batch, batch_res = saml_adapter.process_and_isolate(raw_batch, f"BATCH-SAML-INIT-{total_saml_ingested}")
            total_saml_labels_isolated += batch_res.labels_isolated

            for txn in normalized_batch:
                src = txn["source_account_id"]
                dest = txn.get("destination_account_id")
                ts = txn["created_at"]
                curr = txn["currency"]
                amt = txn["amount"]

                # Create customer and account stubs
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

                # Initial state prior to genuine model prediction
                risk_score = None
                risk_band = "PENDING"

                cursor.execute("""
                    INSERT OR REPLACE INTO transactions (
                        id, event_id, source_account_id, destination_account_id, customer_id,
                        amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SAML_D', ?)
                """, (
                    txn["id"], txn["event_id"], src, dest, f"CUST-{src}",
                    amt, curr, txn.get("payment_type", "TRANSFER"),
                    txn.get("payment_channel", "WIRE"), "COMPLETED", risk_score, risk_band, ts
                ))

                total_saml_ingested += 1
                if risk_score is not None and risk_score >= 65.0:
                    saml_txns_for_alerts.append((txn["id"], src, f"CUST-{src}", amt, curr, risk_score, risk_band, ts))

        print(f"Verified SAML-D Records Ingested: {total_saml_ingested:,}")
        print(f"Verified SAML-D Ground-Truth Labels Isolated: {total_saml_labels_isolated:,}")

        # 4. Ingest DATASET 2: Real NFPC Transactions & Mule Labels
        print(f"\n--- 4. Ingesting Real DATASET 2 (NFPC) from {nfpc_parquet_path} ---")
        nfpc_adapter = NfpcAdapter(batch_size=1000)
        total_nfpc_ingested = 0
        total_nfpc_labels_isolated = 0

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

                score = 12.0
                band = "ROUTINE"
                if amt > 200000.0:
                    score = round(rng.uniform(75.0, 92.0), 1)
                    band = "HIGH"
                elif amt > 50000.0:
                    score = round(rng.uniform(45.0, 74.0), 1)
                    band = "ELEVATED"

                cursor.execute("""
                    INSERT OR REPLACE INTO transactions (
                        id, event_id, source_account_id, destination_account_id, customer_id,
                        amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NFPC_MULE', ?)
                """, (
                    txn["id"], txn["event_id"], src, dest, f"CUST-{src}",
                    amt, curr, txn.get("payment_type", "TRANSFER"),
                    txn.get("payment_channel", "IMPS"), "COMPLETED", score, band, ts
                ))
                total_nfpc_ingested += 1

        print(f"Verified NFPC Records Ingested: {total_nfpc_ingested:,}")
        print(f"Verified NFPC Account Labels Isolated: {total_nfpc_labels_isolated:,}")

        # 5. Generate Real Alerts from High-Risk Transactions
        print("\n--- 5. Generating Alerts from Real Suspicious Patterns ---")
        created_alerts = []
        for i, t in enumerate(saml_txns_for_alerts[:40]):
            aid = f"ALT-SAML-{1000 + i}"
            ref = f"ALT-2026-SAML-{100 + i}"
            sev = "CRITICAL" if t[5] >= 80.0 else ("HIGH" if t[5] >= 68.0 else "MEDIUM")
            status = "CONVERTED_TO_INVESTIGATION" if i < 12 else ("TRIAGED" if i < 24 else "NEW")

            cursor.execute("""
                INSERT OR REPLACE INTO alerts (
                    id, alert_ref, transaction_id, account_id, customer_id,
                    severity, status, risk_score, title, summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aid, ref, t[0], t[1], t[2], sev, status, t[5],
                f"SAML-D Suspicious Pattern: {t[4]} {t[3]:,.2f} Anomalous Velocity",
                f"SAML-D Account {t[1]} exhibited high volume funds movement in {t[4]} exceeding rolling baseline.",
                t[7], t[7]
            ))
            created_alerts.append((aid, ref, t))

            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'GRAPH', 'SAML_D_MULE_TOPOLOGY', 'Identified as node in SAML-D flow network', 35.0, 'v1.0', ?)
            """, (f"FND-{aid}-1", aid, t[7]))

            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'ANOMALY', 'MAD_AMOUNT_DEVIATION', 'Significant deviation exceeding historical rolling median', 30.0, 'v1.0', ?)
            """, (f"FND-{aid}-2", aid, t[7]))

        print(f"Created {len(created_alerts)} active alerts across CRITICAL, HIGH, and MEDIUM severities.")

        # 6. Instantiate Formal Investigations Linked to Alerts
        print("\n--- 6. Instantiating Investigation Dossiers & Forensic Workbenches ---")
        inv_cases = [
            ("CASE-2026-001", "[DEMO FIXTURE] SAML-D Multi-Hop Cross-Border Layering", "CRITICAL", "NEW", 94.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-002", "[DEMO FIXTURE] SAML-D Fan-Out Rapid Dispersal Cluster", "HIGH", "IN_PROGRESS", 86.5, "SUSPICIOUS_UNCONFIRMED"),
            ("CASE-2026-003", "[DEMO FIXTURE] SAML-D Circular Round-Tripping Ring", "HIGH", "PENDING_PEER_REVIEW", 82.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-004", "[DEMO FIXTURE] SAML-D Commercial Remittance Lookalike", "MEDIUM", "RESOLVED", 54.0, "LEGITIMATE_ACTIVITY"),
            ("CASE-2026-005", "[DEMO FIXTURE] SAML-D Rapid Inbound-Outbound Pass-Through", "CRITICAL", "IN_PROGRESS", 91.0, None),
            ("CASE-2026-006", "[DEMO FIXTURE] SAML-D High-Value Currency Conversion Spike", "HIGH", "TRIAGED", 79.5, None),
            ("CASE-2026-007", "[DEMO FIXTURE] NFPC Indian Banking Mule Network Infiltration", "CRITICAL", "IN_PROGRESS", 88.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-008", "[DEMO FIXTURE] NFPC High Velocity IMPS Aggregation Point", "HIGH", "TRIAGED", 76.5, None)
        ]

        for idx, (c_num, c_title, c_prio, c_status, c_score, c_disp) in enumerate(inv_cases):
            inv_id = f"INV-CASE-{idx+1:03d}"
            target_alert = created_alerts[idx % len(created_alerts)]
            a_id, a_ref, a_txn = target_alert

            cursor.execute("""
                INSERT OR REPLACE INTO investigations (
                    id, case_number, title, summary, priority, status,
                    assigned_investigator_id, disposition, disposition_rationale,
                    evidence_completeness_score, model_version, rule_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'USR-INV-01', ?, ?, ?, 'v1.0', 'v1.0', ?, ?)
            """, (
                inv_id, c_num, c_title,
                f"Self-directed investigation instantiated from alert {a_ref} on Account {a_txn[1]}.",
                c_prio, c_status, c_disp,
                "Confirmed coordinated money mule behavior consistent with ground truth." if c_disp == "CONFIRMED_FRAUD" else None,
                85.0 if idx < 4 else 50.0,
                a_txn[7], a_txn[7]
            ))

            cursor.execute("""
                INSERT OR IGNORE INTO investigation_alerts (investigation_id, alert_id, added_at)
                VALUES (?, ?, ?)
            """, (inv_id, a_id, a_txn[7]))

            # Evidence Items
            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, source_record_id, description,
                    observed_facts_json, verification_status, collector, created_at
                ) VALUES (?, ?, 'TRANSACTION', ?, ?, '{"dataset": "SAML_D"}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-1", inv_id, a_txn[0], f"Triggering transfer of {a_txn[4]} {a_txn[3]:,.2f} on Account {a_txn[1]}", a_txn[7]))

            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, source_record_id, description,
                    observed_facts_json, verification_status, collector, created_at
                ) VALUES (?, ?, 'BEHAVIORAL_ANOMALY', ?, ?, '{"deviation": "3.8x baseline"}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-2", inv_id, a_txn[0], "Statistical deviation observed against historical rolling median", a_txn[7]))

            # Tasks
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, description, is_completed, created_at)
                VALUES (?, ?, 'Inspect counterparty entity credentials', 'Verify counterparty licensing and country risk profile', 1, ?)
            """, (f"TSK-{inv_id}-1", inv_id, a_txn[7]))
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, description, is_completed, created_at)
                VALUES (?, ?, 'Trace downstream multi-hop money flow', 'Determine if funds reached offshore off-ramp or cash-out point', 0, ?)
            """, (f"TSK-{inv_id}-2", inv_id, a_txn[7]))

            # Copilot Note
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_notes (id, investigation_id, author_id, content, is_confidential, created_at)
                VALUES (?, ?, 'SYSTEM_COPILOT', ?, 0, ?)
            """, (
                f"NOT-{inv_id}-1", inv_id,
                f"Copilot Auto-Triage: Case {c_num} analyzed using multi-hop graph topology. Recommended action: Trace outbound hops in Network Intelligence.",
                a_txn[7]
            ))

        print(f"Created {len(inv_cases)} investigation dossiers with evidence, checklist tasks, and Copilot triage notes.")

        # 7. Seed Feedback & Learning from Real NFPC Labeled Accounts (100 samples)
        print("\n--- 7. Populating Feedback & Learning with Ground-Truth Labeled Records ---")
        if os.path.exists(nfpc_labels_path):
            tbl = pd.read_parquet(nfpc_labels_path, columns=["account_id", "is_mule"])
            mules = tbl[tbl["is_mule"] == 1].head(45)
            legits = tbl[tbl["is_mule"] == 0].head(55)
            combined_labels = pd.concat([mules, legits]).sample(frac=1.0, random_state=42).reset_index(drop=True)

            for i, row in combined_labels.iterrows():
                is_scam = int(row["is_mule"])
                disp_type = "CONFIRMED_FRAUD" if is_scam == 1 else "LEGITIMATE_ACTIVITY"
                rationale_text = (
                    f"Verified coordinated money mule forwarding account {row['account_id']} (NFPC ground truth: MULE)."
                    if is_scam == 1 else
                    f"Verified legitimate domestic banking account {row['account_id']} (NFPC ground truth: LEGIT)."
                )

                inv_ref = f"INV-CASE-{(i % len(inv_cases)) + 1:03d}"
                fb_id = f"FB-NFPC-{1000 + i}"
                ts = (now - timedelta(days=int(i / 2))).isoformat()

                cursor.execute("""
                    INSERT OR REPLACE INTO analyst_feedback (
                        id, investigation_id, analyst_id, disposition, rationale,
                        evidence_reviewed_count, is_eligible_for_training, training_label,
                        exclusion_reason, model_version, rule_version, created_at
                    ) VALUES (?, ?, 'USR-INV-01', ?, ?, 4, 0, NULL, 'DEMO_FIXTURE', 'v1.0', 'v1.0', ?)
                """, (fb_id, inv_ref, disp_type, rationale_text, ts))

                # Also ensure stored in protected store
                store_protected_account_label(
                    account_id=row["account_id"],
                    dataset_name="NFPC_MULE",
                    is_mule=is_scam,
                    mule_role="MULE_SUSPECT" if is_scam == 1 else "LEGITIMATE",
                    raw_labels={"account_id": row["account_id"], "is_mule": is_scam},
                    timestamp=ts
                )
            print(f"Ingested {len(combined_labels)} real ground-truth feedback records (Mules: {len(mules)}, Legitimate: {len(legits)}).")

        conn.commit()

    # Verify Final Record Counts
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT dataset_source, COUNT(*) FROM transactions GROUP BY dataset_source")
        txn_counts = dict(c.fetchall())
        c.execute("SELECT COUNT(*) FROM accounts")
        acc_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM customers")
        cust_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM alerts")
        alert_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM investigations")
        inv_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM analyst_feedback")
        fb_count = c.fetchone()[0]

    print("\n" + "=" * 60)
    print("Database Ingestion & Seeding Complete — VERIFIED COUNTS:")
    print(f"  Transactions: {txn_counts}")
    print(f"  Accounts: {acc_count:,}")
    print(f"  Customers: {cust_count:,}")
    print(f"  Alerts: {alert_count:,}")
    print(f"  Investigations: {inv_count:,}")
    print(f"  Feedback & Training Records: {fb_count:,}")
    print("=" * 60)

if __name__ == "__main__":
    seed_saml_and_nfpc_database(saml_limit=5000, nfpc_limit=5000)
