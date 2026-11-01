import unittest
import sqlite3
from app.core.database import SCHEMA_SQL
from app.repositories.transaction_repository import create_transaction
from app.api.v1.fund_flow import get_fund_flow
from app.api.v1.audit import get_audit_trail
from app.services.audit_service import record_audit_event

class TestFundFlowAndAudit(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)

        self.originator = "ACC-TEST-ORIG-1"
        self.mule = "ACC-TEST-MULE-1"
        self.beneficiary = "ACC-TEST-BENE-1"

        # Seed hop 1
        self.txn1 = create_transaction(self.conn, {
            "event_id": "EVT-TEST-001",
            "source_account_id": self.originator,
            "destination_account_id": self.mule,
            "amount": 500000.0,
            "currency": "INR",
            "customer_id": "CUST-001",
            "payment_channel": "IMPS",
            "risk_score": 75.0,
            "risk_band": "HIGH"
        })
        # Seed hop 2
        self.txn2 = create_transaction(self.conn, {
            "event_id": "EVT-TEST-002",
            "source_account_id": self.mule,
            "destination_account_id": self.beneficiary,
            "amount": 490000.0,
            "currency": "INR",
            "customer_id": "CUST-002",
            "payment_channel": "RTGS",
            "risk_score": 85.0,
            "risk_band": "CRITICAL"
        })
        self.conn.commit()

        # Seed audit event
        record_audit_event(
            conn=self.conn,
            actor_id="analyst-1",
            actor_name="Analyst One",
            action="OPEN_CASE",
            resource_type="TRANSACTION",
            resource_id=self.txn1["id"],
            metadata={"reason": "Mule chain detected"}
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_fund_flow_network_construction(self):
        res = get_fund_flow(currency="INR", limit=10, db=self.conn)
        self.assertIn("nodes", res)
        self.assertIn("links", res)
        self.assertIn("summary", res)
        self.assertGreater(len(res["nodes"]), 0)
        self.assertGreater(len(res["links"]), 0)

        # Intermediary mule should be recognized
        node_tiers = {n["id"]: n["tier"] for n in res["nodes"]}
        if self.mule in node_tiers:
            self.assertEqual(node_tiers[self.mule], "intermediary")

    def test_audit_trail_filtering_by_resource_id(self):
        res = get_audit_trail(
            page=1,
            page_size=10,
            resource_id=self.txn1["id"],
            current_user={"id": "test_user"},
            db=self.conn
        )
        self.assertIn("items", res)
        self.assertIn("total", res)
        self.assertGreaterEqual(res["total"], 1)
        found = any(item.get("resource_id") == self.txn1["id"] for item in res["items"])
        self.assertTrue(found)

if __name__ == "__main__":
    unittest.main()
