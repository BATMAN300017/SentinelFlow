import time
import random
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.core.database import transaction_scope
from app.services.transaction_ingestion import ingest_transaction_event
from app.utils.ids import generate_id, generate_transaction_id
from app.utils.time import utc_now_iso
from app.core.guards import check_demo_environment_guard

class TransactionSimulator:
    def __init__(self):
        self._is_running = False
        self._is_paused = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._seed = 42
        self._events_emitted = 0
        self._alerts_triggered = 0
        self._status = "IDLE"
        self._active_scenario = "NORMAL_OPERATIONS"

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "is_running": self._is_running,
                "is_paused": self._is_paused,
                "active_scenario": self._active_scenario,
                "events_emitted": self._events_emitted,
                "alerts_triggered": self._alerts_triggered,
                "seed": self._seed
            }

    def start_simulation(self, scenario: str = "NORMAL_OPERATIONS", interval_sec: float = 1.5):
        check_demo_environment_guard("Transaction simulation")
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._is_paused = False
            self._status = "RUNNING"
            self._active_scenario = scenario

        self._thread = threading.Thread(target=self._run_loop, args=(interval_sec,), daemon=True)
        self._thread.start()

    def pause_simulation(self):
        with self._lock:
            if self._is_running and not self._is_paused:
                self._is_paused = True
                self._status = "PAUSED"

    def resume_simulation(self):
        with self._lock:
            if self._is_running and self._is_paused:
                self._is_paused = False
                self._status = "RUNNING"

    def stop_simulation(self):
        with self._lock:
            self._is_running = False
            self._is_paused = False
            self._status = "STOPPED"

    def run_named_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Runs a deterministic 1-shot batch of scenario transactions."""
        check_demo_environment_guard("Deterministic scenario simulation")
        rng = random.Random(self._seed + hash(scenario_name) % 1000)
        events_batch = []
        
        with transaction_scope() as conn:
            # Fetch sample accounts
            cursor = conn.cursor()
            cursor.execute("SELECT id, customer_id FROM accounts LIMIT 20")
            acc_rows = cursor.fetchall()
            if not acc_rows:
                return {"error": "No seeded accounts available. Please run data seeding first."}
                
            accounts = [(r[0], r[1]) for r in acc_rows]
            
            if scenario_name.lower() in ("rapid_movement", "scenario_a"):
                # Scenario A: Rapid fund movement
                # Acc 0 receives 15,000 inbound, then within minutes forwards 13,800 to Acc 1
                acc_target = accounts[0][0]
                acc_cust = accounts[0][1]
                acc_dest = accounts[1][0]
                now = datetime.now(timezone.utc)
                
                # Inbound transfer
                e1 = {
                    "event_id": f"SIM-EVT-{generate_id()}",
                    "source_account_id": accounts[2][0],
                    "destination_account_id": acc_target,
                    "beneficiary_name": f"Account {acc_target}",
                    "customer_id": accounts[2][1],
                    "amount": 16500.0,
                    "currency": "USD",
                    "transaction_type": "TRANSFER",
                    "payment_channel": "WIRE",
                    "scenario_id": "SCENARIO_A_RAPID_MOVEMENT",
                    "is_ground_truth_fraud": 1,
                    "created_at": (now - timedelta(minutes=12)).isoformat()
                }
                res1 = ingest_transaction_event(conn, e1)
                events_batch.append(res1)
                
                # Immediate rapid outbound
                e2 = {
                    "event_id": f"SIM-EVT-{generate_id()}",
                    "source_account_id": acc_target,
                    "destination_account_id": acc_dest,
                    "beneficiary_name": f"External Offshore LLC",
                    "customer_id": acc_cust,
                    "amount": 15200.0,
                    "currency": "USD",
                    "transaction_type": "TRANSFER",
                    "payment_channel": "ONLINE",
                    "scenario_id": "SCENARIO_A_RAPID_MOVEMENT",
                    "is_ground_truth_fraud": 1,
                    "created_at": now.isoformat()
                }
                res2 = ingest_transaction_event(conn, e2)
                events_batch.append(res2)
                
            elif scenario_name.lower() in ("connected_network", "scenario_b"):
                # Scenario B: Connected Account Network with Shared Device
                shared_dev = f"DEV-CLUSTER-987"
                now = datetime.now(timezone.utc)
                collector = accounts[3][0]
                
                for i in range(4):
                    src_acc = accounts[i+4][0]
                    e = {
                        "event_id": f"SIM-EVT-{generate_id()}",
                        "source_account_id": src_acc,
                        "destination_account_id": collector,
                        "beneficiary_name": f"Consolidation Hub",
                        "customer_id": accounts[i+4][1],
                        "amount": 4200.0 + (i * 300),
                        "currency": "USD",
                        "transaction_type": "TRANSFER",
                        "payment_channel": "MOBILE_APP",
                        "device_id": shared_dev,
                        "scenario_id": "SCENARIO_B_CONNECTED_NETWORK",
                        "is_ground_truth_fraud": 1,
                        "created_at": (now - timedelta(minutes=5 * (4 - i))).isoformat()
                    }
                    res = ingest_transaction_event(conn, e)
                    events_batch.append(res)
                    
            elif scenario_name.lower() in ("legitimate_unusual", "scenario_c"):
                # Scenario C: Benign high-value purchase on established account
                established_acc = accounts[0][0]
                e = {
                    "event_id": f"SIM-EVT-{generate_id()}",
                    "source_account_id": established_acc,
                    "customer_id": accounts[0][1],
                    "amount": 8900.0,
                    "currency": "USD",
                    "transaction_type": "MERCHANT_PAYMENT",
                    "payment_channel": "POS",
                    "beneficiary_name": "Nordic Travel Luxury Expeditions",
                    "scenario_id": "SCENARIO_C_LEGITIMATE_UNUSUAL",
                    "is_ground_truth_fraud": 0,
                    "created_at": utc_now_iso()
                }
                res = ingest_transaction_event(conn, e)
                events_batch.append(res)
                
            self._events_emitted += len(events_batch)
            
        return {
            "scenario": scenario_name,
            "events_created": len(events_batch),
            "results": events_batch
        }

    def _run_loop(self, interval_sec: float):
        rng = random.Random(self._seed)
        channels = ["ONLINE", "MOBILE_APP", "POS", "ATM", "WIRE"]
        types = ["TRANSFER", "CARD_PAYMENT", "MERCHANT_PAYMENT"]
        
        while self._is_running:
            if self._is_paused:
                time.sleep(0.5)
                continue
                
            try:
                with transaction_scope() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, customer_id FROM accounts ORDER BY RANDOM() LIMIT 2")
                    rows = cursor.fetchall()
                    if len(rows) >= 2:
                        src_acc, src_cust = rows[0]
                        dest_acc, _ = rows[1]
                        amt = round(rng.uniform(15.0, 1200.0), 2)
                        
                        evt = {
                            "event_id": f"STREAM-TXN-{generate_id()}",
                            "source_account_id": src_acc,
                            "destination_account_id": dest_acc,
                            "beneficiary_name": f"Account {dest_acc}",
                            "customer_id": src_cust,
                            "amount": amt,
                            "currency": "USD",
                            "transaction_type": rng.choice(types),
                            "payment_channel": rng.choice(channels),
                            "device_id": f"DEV-{rng.randint(100, 999)}",
                            "ip_address": f"192.168.1.{rng.randint(10, 250)}",
                            "created_at": utc_now_iso()
                        }
                        res = ingest_transaction_event(conn, evt)
                        self._events_emitted += 1
                        if res.get("alert_created"):
                            self._alerts_triggered += 1
            except Exception as ex:
                pass
                
            time.sleep(interval_sec)

simulation_service = TransactionSimulator()
