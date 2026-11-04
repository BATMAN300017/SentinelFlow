import os
import sys
import random
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import init_db, transaction_scope
from app.core.security import hash_password
from app.utils.ids import (
    generate_customer_id, generate_account_id, generate_transaction_id,
    generate_alert_id, generate_investigation_id, generate_evidence_id, generate_user_id
)
from app.detection.rules import ensure_default_rules
from app.core.guards import check_demo_environment_guard

def seed_demo_database():
    check_demo_environment_guard()
    print("Initializing SentinelFlow AI demo database...")
    init_db()
    
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    
    with transaction_scope() as conn:
        cursor = conn.cursor()
        
        # 1. Seed Demo Users
        print("Seeding demo users...")
        users = [
            ("USR-INV-01", "sarah_investigator", "sarah.lin@sentinelflow.bank", "Sarah Lin", "investigator"),
            ("USR-SR-02", "marcus_senior", "marcus.vance@sentinelflow.bank", "Marcus Vance", "senior_investigator"),
            ("USR-ADM-03", "elena_admin", "elena.rostova@sentinelflow.bank", "Elena Rostova", "fraud_admin"),
            ("USR-AUD-04", "arthur_auditor", "arthur.pendelton@sentinelflow.bank", "Arthur Pendelton", "auditor"),
        ]
        pwd_hash = hash_password("password123")
        for u_id, uname, email, fname, role in users:
            cursor.execute("""
                INSERT OR REPLACE INTO users (id, username, email, full_name, role, hashed_password, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (u_id, uname, email, fname, role, pwd_hash, (now - timedelta(days=90)).isoformat()))
            
        # 2. Seed 100 Customers
        print("Seeding 100 fictional customers...")
        first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Lucas", "Sophia", "Oliver", "Isabella", "David", "Mia", "Benjamin", "Charlotte", "Henry", "Amelia", "Alexander", "Harper", "Sebastian", "Evelyn"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
        tiers = ["STANDARD", "STANDARD", "STANDARD", "LOW", "HIGH"]
        
        customer_ids = []
        for i in range(100):
            cid = f"CUST-{1000 + i}"
            fn = first_names[i % len(first_names)]
            ln = last_names[(i * 3) % len(last_names)]
            full = f"{fn} {ln}"
            email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
            tier = tiers[i % len(tiers)]
            cursor.execute("""
                INSERT OR REPLACE INTO customers (id, customer_ref, full_name, email, phone, risk_tier, kyc_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'VERIFIED', ?)
            """, (cid, f"REF-{1000+i}", full, email, f"+1-555-01{i:02d}", tier, (now - timedelta(days=120)).isoformat()))
            customer_ids.append(cid)
            
        # 3. Seed 150 Accounts
        print("Seeding 150 accounts...")
        account_ids = []
        types = ["CHECKING", "CHECKING", "SAVINGS", "BUSINESS"]
        for i in range(150):
            aid = f"ACT-{2000 + i}"
            cid = customer_ids[i % len(customer_ids)]
            acc_num = f"4009-8812-{i:04d}"
            bal = round(rng.uniform(250.0, 48000.0), 2)
            is_dormant = 1 if (i % 25 == 0) else 0
            cursor.execute("""
                INSERT OR REPLACE INTO accounts (id, account_number, customer_id, account_type, currency, balance, status, is_dormant, created_at)
                VALUES (?, ?, ?, ?, 'USD', ?, 'ACTIVE', ?, ?)
            """, (aid, acc_num, cid, types[i % len(types)], bal, is_dormant, (now - timedelta(days=180)).isoformat()))
            account_ids.append(aid)
            
        # 4. Seed Rules
        ensure_default_rules(conn)
        
        # 5. Seed 1,000 Historical Transactions
        print("Seeding 1,000 transactions...")
        channels = ["ONLINE", "MOBILE_APP", "POS", "ATM", "WIRE"]
        txn_types = ["TRANSFER", "CARD_PAYMENT", "MERCHANT_PAYMENT"]
        
        txns_list = []
        for i in range(1000):
            tid = f"TXN-{10000 + i}"
            eid = f"EVT-{10000 + i}"
            src = account_ids[i % len(account_ids)]
            dst = account_ids[(i * 7 + 1) % len(account_ids)]
            cust = customer_ids[i % len(customer_ids)]
            
            # Create mixture of amounts
            if i % 40 == 0:
                amt = round(rng.uniform(7500.0, 24000.0), 2) # High value burst
                score = round(rng.uniform(65.0, 92.0), 1)
                band = "HIGH" if score >= 75 else "ELEVATED"
            elif i % 15 == 0:
                amt = round(rng.uniform(1500.0, 4800.0), 2)
                score = round(rng.uniform(30.0, 55.0), 1)
                band = "LOW" if score < 50 else "ELEVATED"
            else:
                amt = round(rng.uniform(12.50, 450.0), 2)
                score = round(rng.uniform(2.0, 22.0), 1)
                band = "ROUTINE"
                
            t_time = (now - timedelta(days=rng.randint(0, 14), minutes=rng.randint(0, 1440))).isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO transactions (
                    id, event_id, source_account_id, destination_account_id, beneficiary_name,
                    customer_id, amount, currency, transaction_type, payment_channel,
                    device_id, ip_address, status, risk_score, risk_band, dataset_source, scenario_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?, 'COMPLETED', ?, ?, 'DEMO_FIXTURE', 'DEMO_FIXTURE', ?)
            """, (
                tid, eid, src, dst, f"Counterparty {dst}", cust, amt,
                rng.choice(txn_types), rng.choice(channels), f"DEV-{100 + (i % 30)}",
                f"10.0.{i % 10}.{i % 250}", score, band, t_time
            ))
            txns_list.append((tid, src, cust, amt, score, band, t_time))
            
        # 6. Seed 30 Alerts
        print("Seeding 30 alerts with varied severities and findings...")
        alert_ids = []
        high_risk_txns = [t for t in txns_list if t[4] >= 50.0]
        for i in range(min(30, len(high_risk_txns))):
            t = high_risk_txns[i]
            aid = f"ALT-{3000 + i}"
            ref = f"ALT-2026-{100 + i}"
            sev = "CRITICAL" if t[4] >= 80 else ("HIGH" if t[4] >= 65 else "MEDIUM")
            stat = "CONVERTED_TO_INVESTIGATION" if i < 12 else ("TRIAGED" if i < 20 else "NEW")
            
            cursor.execute("""
                INSERT OR REPLACE INTO alerts (
                    id, alert_ref, transaction_id, account_id, customer_id,
                    severity, status, risk_score, title, summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aid, ref, t[0], t[1], t[2], sev, stat, t[4],
                f"[DEMO FIXTURE] High-Risk Signal: Unusual Transfer of ${t[3]:,.2f}",
                f"[DEMO FIXTURE] Simulated anomaly: Account {t[1]} exhibited unusual transaction velocity and amount deviation.",
                t[6], t[6]
            ))
            alert_ids.append(aid)
            
            # Finding
            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'DEMO_FIXTURE', 'DEMO_VELOCITY', '[DEMO FIXTURE] Multiple consecutive transfers within short lookback window', 40.0, 'v1', ?)
            """, (f"FND-{i}", aid, t[6]))
            
        # 7. Seed 10 Investigations across lifecycle stages
        print("Seeding 10 investigations across lifecycle stages...")
        statuses = ["NEW", "TRIAGED", "IN_PROGRESS", "PENDING_PEER_REVIEW", "RESOLVED"]
        dispositions = [
            ("CONFIRMED_FRAUD", "Unauthorized account takeover resulting in rapid outgoing wire forwarding."),
            ("LEGITIMATE_ACTIVITY", "Confirmed legitimate capital contribution for commercial real estate acquisition."),
            ("SUSPICIOUS_UNCONFIRMED", "Suspicious layering pattern detected but counterparty is uncooperative."),
            ("INCONCLUSIVE", "Customer unresponsive, transaction was within historical maximum variance.")
        ]
        
        for i in range(10):
            inv_id = f"INV-{4000 + i}"
            case_num = f"CASE-2026-{100 + i}"
            stat = statuses[i % len(statuses)]
            disp = None
            rationale = None
            if stat == "RESOLVED":
                disp, rationale = dispositions[i % len(dispositions)]
            elif stat == "PENDING_PEER_REVIEW":
                disp = "CONFIRMED_FRAUD"
                rationale = "Structured fund transfer chain verified through shared device analysis."
                
            cursor.execute("""
                INSERT OR REPLACE INTO investigations (
                    id, case_number, title, summary, priority, status,
                    assigned_investigator_id, disposition, disposition_rationale,
                    peer_review_status, evidence_completeness_score, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'HIGH', ?, 'USR-INV-01', ?, ?, ?, ?, ?, ?)
            """, (
                inv_id, case_num, f"[DEMO FIXTURE] Priority Case {100 + i}",
                f"Demo investigation fixture into simulated activity on Account {account_ids[i]}.",
                stat, disp, rationale,
                "REQUESTED" if stat == "PENDING_PEER_REVIEW" else "NONE",
                80.0 if stat == "RESOLVED" else 40.0,
                (now - timedelta(days=i + 1)).isoformat(), now.isoformat()
            ))
            
            # Associate alert
            if i < len(alert_ids):
                cursor.execute("""
                    INSERT OR REPLACE INTO investigation_alerts (investigation_id, alert_id, added_at)
                    VALUES (?, ?, ?)
                """, (inv_id, alert_ids[i], now.isoformat()))
                
            # Seed evidence (Marked as DEMO FIXTURE)
            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, description, observed_facts_json,
                    verification_status, collector, created_at
                ) VALUES (?, ?, 'TRANSACTION', '[DEMO FIXTURE] Triggering wire transaction of high monetary value', '{"is_demo_fixture": true}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-1", inv_id, now.isoformat()))
            
            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, description, observed_facts_json,
                    verification_status, collector, created_at
                ) VALUES (?, ?, 'BEHAVIORAL_ANOMALY', '[DEMO FIXTURE] Rolling median deviation robust z-score > 3.5', '{"is_demo_fixture": true}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-2", inv_id, now.isoformat()))
            
            # Tasks
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, is_completed, created_at)
                VALUES (?, ?, 'Inspect triggering transaction & beneficiary', 1, ?)
            """, (f"TSK-{inv_id}-1", inv_id, now.isoformat()))
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, is_completed, created_at)
                VALUES (?, ?, 'Examine shared device cluster', ?, ?)
            """, (f"TSK-{inv_id}-2", inv_id, 1 if stat == "RESOLVED" else 0, now.isoformat()))
            
            # Notes
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_notes (id, investigation_id, author_id, content, created_at)
                VALUES (?, ?, 'USR-INV-01', 'Initial case review completed. Evidence bundle generated.', ?)
            """, (f"NOT-{inv_id}", inv_id, now.isoformat()))
            
            # Feedback for resolved cases (Explicitly excluded from ML training as DEMO_FIXTURE)
            if disp:
                cursor.execute("""
                    INSERT OR REPLACE INTO analyst_feedback (
                        id, investigation_id, analyst_id, disposition, rationale,
                        evidence_reviewed_count, is_eligible_for_training, training_label,
                        exclusion_reason, model_version, rule_version, created_at
                    ) VALUES (?, ?, 'USR-INV-01', ?, ?, 4, 0, NULL, 'DEMO_FIXTURE', 'v1.0', 'v1.0', ?)
                """, (
                    f"FDB-{inv_id}", inv_id, disp, rationale,
                    now.isoformat()
                ))

    print("Deterministic demo seeding successfully completed!")

if __name__ == "__main__":
    seed_demo_database()
