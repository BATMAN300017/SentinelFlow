import unittest
import os
import sys
import sqlite3

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.api.v1.health import health_check
from app.api.v1.auth import login, LoginRequest
from app.api.v1.dashboard import get_dashboard_summary, get_dashboard_trends
from app.api.v1.transactions import get_transactions
from app.api.v1.alerts import get_alerts
from app.api.v1.investigations import get_all_investigations
from app.api.v1.graph import get_graph
from app.api.v1.feedback import get_learning_status
from app.api.v1.rules import list_detection_rules
from app.core.database import get_db_connection

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        from app.core.database import SCHEMA_SQL
        from app.detection.rules import ensure_default_rules
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_health_check_endpoint(self):
        res = health_check(self.conn)
        self.assertEqual(res["status"], "healthy")
        self.assertTrue(res["database_connected"])

    def test_auth_login_with_demo_credentials(self):
        req = LoginRequest(username="sarah_investigator", password="password123")
        res = login(req, self.conn)
        self.assertIn("access_token", res)
        self.assertEqual(res["role"], "investigator")

    def test_dashboard_summary(self):
        res = get_dashboard_summary(self.conn)
        self.assertIn("transactions_processed", res)
        self.assertIn("alerts_generated", res)

    def test_transactions_list(self):
        res = get_transactions(page=1, page_size=5, db=self.conn)
        self.assertIn("items", res)
        self.assertIn("total", res)

    def test_alerts_list(self):
        res = get_alerts(page=1, page_size=5, db=self.conn)
        self.assertIn("items", res)

    def test_investigations_list(self):
        res = get_all_investigations(page=1, page_size=5, db=self.conn)
        self.assertIn("items", res)

    def test_graph_endpoint(self):
        res = get_graph(db=self.conn)
        self.assertIn("nodes", res)
        self.assertIn("edges", res)

    def test_learning_status(self):
        res = get_learning_status(self.conn)
        self.assertIn("current_active_model", res)
        self.assertIn("training_data_readiness", res)

    def test_rules_list(self):
        res = list_detection_rules(self.conn)
        self.assertIsInstance(res, list)
        self.assertGreater(len(res), 0)

    def test_audit_endpoint(self):
        from app.api.v1.audit import get_audit_trail
        res = get_audit_trail(page=1, page_size=10, current_user={"role": "investigator", "username": "sarah_investigator"}, db=self.conn)
        self.assertIn("items", res)
        self.assertIn("total", res)
        self.assertEqual(res["page"], 1)
        self.assertEqual(res["page_size"], 10)

if __name__ == "__main__":
    unittest.main()
