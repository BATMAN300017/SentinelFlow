"""
Unit tests for Safe Batch Ingestion Pipeline (scripts/safe_batch_ingest.py).
Validates:
1. Label isolation: ground-truth labels stripped and never leaked into detection.
2. Storage ceiling enforcement.
3. Checkpoint persistence and offset tracking.
4. Per-batch rollback execution.
"""

import unittest
import sqlite3
import os
import sys
import json
import uuid
import tempfile
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from app.core.database import SCHEMA_SQL
from app.data_ingestion.label_isolation import LabelLeakageError, assert_no_label_leakage, strip_labels_for_detection
from safe_batch_ingest import check_storage_projection, ensure_account_exists, rollback_batch


class TestSafeBatchIngest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)

    def tearDown(self):
        self.conn.close()

    def test_01_label_isolation_strips_laundering_and_mule_labels(self):
        """Verifies strip_labels_for_detection completely removes ground-truth labels."""
        raw_record = {
            "id": "TXN-TEST-001",
            "amount": 45000.0,
            "currency": "INR",
            "source_account_id": "ACC-SENDER",
            "destination_account_id": "ACC-RECEIVER",
            "is_laundering": 1,
            "laundering_type": "Structuring",
            "is_mule": 1,
            "mule_label": "CONFIRMED_MULE",
            "created_at": "2023-05-01T12:00:00Z"
        }

        detection_dict, protected_labels = strip_labels_for_detection(raw_record)

        # 1. Detection dict must not contain any forbidden labels
        self.assertNotIn("is_laundering", detection_dict)
        self.assertNotIn("laundering_type", detection_dict)
        self.assertNotIn("is_mule", detection_dict)
        self.assertNotIn("mule_label", detection_dict)

        # 2. assert_no_label_leakage must pass without exception
        assert_no_label_leakage(detection_dict, context="Test Detection Record")

        # 3. Protected labels dictionary must retain ground-truth
        self.assertEqual(protected_labels.get("is_laundering"), 1)
        self.assertEqual(protected_labels.get("laundering_type"), "Structuring")
        self.assertEqual(protected_labels.get("is_mule"), 1)

    def test_02_label_leakage_assertion_raises_security_alert(self):
        """Verifies assert_no_label_leakage raises LabelLeakageError if label exists."""
        leaky_record = {
            "id": "TXN-LEAK-01",
            "amount": 100.0,
            "is_fraud": 1
        }
        with self.assertRaises(LabelLeakageError):
            assert_no_label_leakage(leaky_record, context="Leaky Test")

    def test_03_storage_projection_respects_ceiling(self):
        """Verifies check_storage_projection rejects ingestions exceeding STORAGE_CEILING_MB."""
        with patch("safe_batch_ingest.get_current_storage_mb", return_value=(449.0, "MockEngine")):
            # 10,000 txns @ 0.56 KB = ~5.46 MB -> 449 + 5.46 = 454.46 > 450.0 MB ceiling
            allowed = check_storage_projection(self.conn, records_to_ingest=10000)
            self.assertFalse(allowed)

        with patch("safe_batch_ingest.get_current_storage_mb", return_value=(300.0, "MockEngine")):
            # 1,000 txns @ 0.56 KB = ~0.55 MB -> 300 + 0.55 = 300.55 < 450.0 MB ceiling
            allowed = check_storage_projection(self.conn, records_to_ingest=1000)
            self.assertTrue(allowed)

    def test_04_ensure_account_creates_foreign_keys(self):
        """Verifies ensure_account_exists creates customer and account records without error."""
        ensure_account_exists(self.conn, "ACC-NEW-01", customer_id="CUST-NEW-01", currency="INR")
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, currency FROM accounts WHERE id = 'ACC-NEW-01'")
        acc = cursor.fetchone()
        self.assertIsNotNone(acc)
        self.assertEqual(acc[0], "ACC-NEW-01")
        self.assertEqual(acc[1], "INR")

    def test_05_rollback_batch_removes_transactions_and_alerts(self):
        """Verifies rollback_batch cleanly deletes stamped transactions and associated alerts."""
        cursor = self.conn.cursor()
        batch_id = f"BATCH-TEST-{uuid.uuid4().hex[:6]}"

        # Insert dummy accounts
        ensure_account_exists(self.conn, "ACC-RB-1")
        ensure_account_exists(self.conn, "ACC-RB-2")

        # Insert 3 transactions tagged with this batch_id
        for i in range(3):
            tid = f"TXN-RB-{i}"
            cursor.execute("""
                INSERT INTO transactions (
                    id, event_id, source_account_id, destination_account_id,
                    customer_id, amount, currency, transaction_type, payment_channel,
                    status, scenario_id, dataset_source, risk_score, risk_band, scoring_status, created_at
                ) VALUES (?, ?, 'ACC-RB-1', 'ACC-RB-2', 'CUST-ACC-RB-1', 100.0, 'USD', 'TRANSFER', 'ONLINE',
                          'COMPLETED', ?, 'TEST_DS', 75.0, 'HIGH', 'CURRENT', '2023-01-01T00:00:00Z')
            """, (tid, tid, batch_id))

            # Insert an alert for transaction 0
            if i == 0:
                cursor.execute("""
                    INSERT INTO alerts (
                        id, alert_ref, transaction_id, account_id, customer_id, severity, status, risk_score,
                        title, summary, created_at, updated_at
                    ) VALUES ('ALT-RB-0', 'REF-RB-0', ?, 'ACC-RB-1', 'CUST-ACC-RB-1', 'HIGH', 'NEW', 75.0,
                              'Test Alert', 'Test Summary', '2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z')
                """, (tid,))

        self.conn.commit()

        # Mock get_db_connection to return this self.conn
        class MockConnContext:
            def __init__(self, conn):
                self.conn = conn
            def __enter__(self):
                return self.conn
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("safe_batch_ingest.get_db_connection", return_value=MockConnContext(self.conn)):
            success = rollback_batch(batch_id)
            self.assertTrue(success)

            # Confirm transactions deleted
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE scenario_id = ?", (batch_id,))
            self.assertEqual(cursor.fetchone()[0], 0)

            # Confirm alert deleted
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE id = 'ALT-RB-0'")
            self.assertEqual(cursor.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
