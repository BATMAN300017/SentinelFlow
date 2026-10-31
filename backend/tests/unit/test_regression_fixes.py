"""
Regression Test Suite for SentinelFlow AI - 5 Production Defect Fixes.

Covers:
1. Issue 1: Alert listing with pagination, column schema (alert_type, detection_reason, assigned_analyst).
2. Issue 2: Graph endpoint Query object handling, bounded hop traversal.
3. Issue 3: Analyst feedback schema compatibility (analyst_decision column).
4. Issue 4: NetworkX dependency import and MuleNetworkEngine graph analysis.
5. Issue 5: Detection scoring regression, rapid fund movement feature extraction, cold-start ensemble weights, and false positive control.
"""

import unittest
import sqlite3
import os
import sys
from fastapi import Query

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.core.database import SCHEMA_SQL, init_db
from app.detection.rules import ensure_default_rules, evaluate_rules
from app.repositories.alert_repository import list_alerts, get_alert_by_id, create_alert
from app.repositories.feedback_repository import record_feedback
from app.graph.builder import build_investigation_subgraph, _normalize_max_hops
from app.api.v1.graph import get_graph
from app.detection.engine import score_transaction
from app.detection.features import extract_transaction_features
from app.detection.ensemble import compute_ensemble_risk
from app.utils.time import utc_now_iso, minutes_ago_iso

class TestRegressionFixes(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)

        # Seed baseline entities
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO customers (id, customer_ref, full_name, email, created_at) VALUES ('CUST-R1', 'REF-R1', 'Regression Test User', 'user@test.in', '2026-01-01')")
        cursor.execute("INSERT INTO accounts (id, account_number, customer_id, balance, is_dormant, currency, created_at) VALUES ('ACT-R1', '9001', 'CUST-R1', 25000.0, 0, 'USD', '2026-01-01')")
        cursor.execute("INSERT INTO accounts (id, account_number, customer_id, balance, is_dormant, currency, created_at) VALUES ('ACT-R2', '9002', 'CUST-R1', 5000.0, 0, 'USD', '2026-01-01')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    # --- ISSUE 1 REGRESSION TESTS ---
    def test_alerts_list_pagination_and_columns(self):
        """Verifies list_alerts and get_alert_by_id properly query alert_type, detection_reason, assigned_analyst."""
        # Insert a transaction
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at)
            VALUES ('TXN-REG-01', 'EVT-REG-01', 'ACT-R1', 'ACT-R2', 'CUST-R1', 9500.0, 'USD', 'TRANSFER', 'ONLINE', '2026-10-31T12:00:00Z')
        """)
        self.conn.commit()

        # Create alert via repository
        alert_data = {
            "id": "ALT-REG-001",
            "transaction_id": "TXN-REG-01",
            "account_id": "ACT-R1",
            "customer_id": "CUST-R1",
            "severity": "CRITICAL",
            "risk_score": 85.5,
            "title": "Regression Alert: Rapid Movement",
            "summary": "Rapid inbound to outbound forwarding",
            "alert_type": "RAPID_FUND_MOVEMENT",
            "detection_reason": "Pass-through velocity exceeded threshold",
            "assigned_to": "USR-ANALYST-1",
            "findings": [{"code": "RAPID_FUND_MOVEMENT", "description": "Forwarding ratio > 80%", "score_contribution": 50.0}]
        }
        created = create_alert(self.conn, alert_data)
        self.assertEqual(created["id"], "ALT-REG-001")

        # Query list_alerts with pagination
        alerts, total = list_alerts(self.conn, limit=10, offset=0)
        self.assertGreaterEqual(total, 1)
        target = next((a for a in alerts if a["id"] == "ALT-REG-001"), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["alert_type"], "RAPID_FUND_MOVEMENT")
        self.assertIn("Pass-through", target["detection_reason"])
        self.assertEqual(target["transaction_amount"], 9500.0)

        # Query get_alert_by_id
        detail = get_alert_by_id(self.conn, "ALT-REG-001")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["alert_type"], "RAPID_FUND_MOVEMENT")
        self.assertEqual(detail["risk_score"], 85.5)

    # --- ISSUE 2 REGRESSION TESTS ---
    def test_graph_hop_bounds_and_query_object(self):
        """Verifies graph traversal handles FastAPI Query defaults, type conversions, and boundary enforcement."""
        # 1. Test Query object as hops (simulates direct endpoint invocation without HTTP context)
        query_obj = Query(2, ge=1, le=3)
        res_subgraph = build_investigation_subgraph(self.conn, ["ACT-R1"], max_hops=query_obj)
        self.assertIn("nodes", res_subgraph)
        self.assertIn("edges", res_subgraph)

        # 2. Test direct get_graph endpoint call (uses default Query parameter)
        res_endpoint = get_graph(account_id="ACT-R1", db=self.conn)
        self.assertIn("nodes", res_endpoint)

        # 3. Test _normalize_max_hops boundary enforcement
        self.assertEqual(_normalize_max_hops(Query(2)), 2)
        self.assertEqual(_normalize_max_hops(None), 2)
        self.assertEqual(_normalize_max_hops("invalid"), 2)
        self.assertEqual(_normalize_max_hops(-5), 1)
        self.assertEqual(_normalize_max_hops(100), 5)
        self.assertEqual(_normalize_max_hops("4"), 4)

    # --- ISSUE 3 REGRESSION TESTS ---
    def test_feedback_migration_and_columns(self):
        """Verifies record_feedback inserts analyst_decision without sqlite3.OperationalError."""
        feedback_data = {
            "investigation_id": "INV-REG-001",
            "analyst_id": "USR-ANALYST-01",
            "disposition": "CONFIRMED_FRAUD",
            "analyst_decision": "CONFIRMED_FRAUD",
            "rationale": "Compromised credential mule flow confirmed.",
            "is_eligible_for_training": 1,
            "training_label": 1
        }
        res = record_feedback(self.conn, feedback_data)
        self.assertIsNotNone(res["id"])

        cursor = self.conn.cursor()
        cursor.execute("SELECT disposition, analyst_decision, is_eligible_for_training FROM analyst_feedback WHERE id = ?", (res["id"],))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["disposition"], "CONFIRMED_FRAUD")
        self.assertEqual(row["analyst_decision"], "CONFIRMED_FRAUD")
        self.assertEqual(row["is_eligible_for_training"], 1)

    # --- ISSUE 4 REGRESSION TESTS ---
    def test_networkx_import_and_mule_engine(self):
        """Verifies networkx is installed and MuleNetworkEngine runs topological graph detection."""
        import networkx as nx
        self.assertTrue(hasattr(nx, "MultiDiGraph"))
        self.assertTrue(hasattr(nx, "pagerank"))

        from app.graph.mule_network_engine import MuleNetworkEngine
        engine = MuleNetworkEngine(self.conn)
        self.assertIsNotNone(engine.graph)
        hubs = engine.discover_fan_in_and_fan_out()
        self.assertIn("fan_in_hubs", hubs)
        self.assertIn("fan_out_hubs", hubs)

    # --- ISSUE 5 REGRESSION TESTS ---
    def test_suspicious_scoring_bounds_and_rapid_movement(self):
        """Verifies rapid inbound-outbound forwarding generates risk_score >= 45.0, while normal txns remain low."""
        now_iso = utc_now_iso()
        five_mins_ago = minutes_ago_iso(5)

        # 1. Inbound transfer of 10,000
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at)
            VALUES ('TXN-IN-REG', 'EVT-IN-REG', 'ACT-R2', 'ACT-R1', 'CUST-R1', 10000.0, 'USD', 'WIRE', 'WIRE', ?)
        """, (five_mins_ago,))
        self.conn.commit()

        # 2. Outbound transfer of 9,200 (92% pass-through within 5 mins)
        outbound_evt = {
            "id": "TXN-OUT-REG",
            "event_id": "EVT-OUT-REG",
            "source_account_id": "ACT-R1",
            "destination_account_id": "ACT-R2",
            "customer_id": "CUST-R1",
            "amount": 9200.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ONLINE",
            "created_at": now_iso
        }

        # Verify feature extraction derives recent_inbound_sum
        features = extract_transaction_features(self.conn, outbound_evt)
        self.assertIn("recent_inbound_sum", features)
        self.assertGreaterEqual(features["recent_inbound_sum"], 10000.0)

        # Verify RAPID_FUND_MOVEMENT rule triggers
        triggered_rules = evaluate_rules(self.conn, outbound_evt, features)
        rule_codes = [r["rule_code"] for r in triggered_rules]
        self.assertIn("RAPID_FUND_MOVEMENT", rule_codes)

        # Verify composite detection engine score
        detection_res = score_transaction(self.conn, outbound_evt)
        self.assertGreaterEqual(detection_res["final_risk_score"], 45.0)

        # 3. False Positive Control: Normal $50 routine transfer from established account
        normal_evt = {
            "id": "TXN-NORM-REG",
            "event_id": "EVT-NORM-REG",
            "source_account_id": "ACT-R1",
            "destination_account_id": "ACT-R2",
            "customer_id": "CUST-R1",
            "amount": 50.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ONLINE",
            "created_at": now_iso
        }
        normal_res = score_transaction(self.conn, normal_evt)
        self.assertLess(normal_res["final_risk_score"], 25.0)

if __name__ == "__main__":
    unittest.main()
