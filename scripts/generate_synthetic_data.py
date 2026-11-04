import os
import sys
import argparse
import random
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import transaction_scope
from app.services.transaction_ingestion import ingest_transaction_event
from app.utils.ids import generate_id
from app.utils.time import utc_now_iso
from app.core.guards import check_demo_environment_guard

def generate_transactions(count: int = 200, seed: int = 42):
    check_demo_environment_guard("Synthetic transaction generation")
    rng = random.Random(seed)
    print(f"Generating {count} synthetic transactions with random seed {seed}...")
    
    with transaction_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, customer_id FROM accounts")
        accounts = cursor.fetchall()
        if not accounts:
            print("No accounts found. Please run seed_demo_data.py first.")
            return
            
        now = datetime.now(timezone.utc)
        channels = ["ONLINE", "MOBILE_APP", "POS", "ATM", "WIRE"]
        types = ["TRANSFER", "CARD_PAYMENT", "MERCHANT_PAYMENT"]
        
        alerts_count = 0
        for i in range(count):
            src, cust = rng.choice(accounts)
            dst, _ = rng.choice(accounts)
            while dst == src:
                dst, _ = rng.choice(accounts)
                
            # Periodic suspicious burst
            if i % 15 == 0:
                amt = round(rng.uniform(6000.0, 18000.0), 2)
            else:
                amt = round(rng.uniform(10.0, 800.0), 2)
                
            evt = {
                "event_id": f"GEN-EVT-{generate_id()}",
                "source_account_id": src,
                "destination_account_id": dst,
                "beneficiary_name": f"Account {dst}",
                "customer_id": cust,
                "amount": amt,
                "currency": "USD",
                "transaction_type": rng.choice(types),
                "payment_channel": rng.choice(channels),
                "device_id": f"DEV-{rng.randint(100, 300)}",
                "ip_address": f"172.16.{rng.randint(1, 5)}.{rng.randint(1, 250)}",
                "created_at": (now - timedelta(minutes=i * 3)).isoformat()
            }
            res = ingest_transaction_event(conn, evt)
            if res.get("alert_created"):
                alerts_count += 1
                
        print(f"Generated {count} transactions successfully! Triggered {alerts_count} alerts.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_transactions(count=args.count, seed=args.seed)
