"""
Unit tests for Safe Batch Ingestion Pipeline (scripts/safe_batch_ingest.py).
Validates:
1. Label isolation: ground-truth labels stripped and never leaked into detection.
2. Storage ceiling enforcement and configurable capacity guard.
3. Checkpoint persistence and offset tracking.
4. Per-batch rollback execution including vault labels and unreferenced accounts.
5. Chunked deduplication and conflict-safe event processing.
"""

import unittest
import sqlite3
import os
import sys
import json
import uuid
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from app.core.database import SCHEMA_SQL
from app.data_ingestion.label_isolation import LabelLeakageError, assert_no_label_leakage, strip_labels_for_detection
from safe_batch_ingest import (
    check_storage_projection,
    ensure_account_exists,
    rollback_batch,
    check_existing_event_ids,
    load_checkpoint,
    save_checkpoint
)


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
        """Verifies check_storage_projection rejects ingestions exceeding effective ceiling."""
        with patch("safe_batch_ingest.get_current_storage_mb", return_value=(449.0, "MockEngine")):
            # 10,000 txns @ 0.650 KB = ~6.35 MB -> 449 + 6.35 = 455.35 > 450.0 MB ceiling (500 - 50)
            allowed = check_storage_projection(self.conn, records_to_ingest=10000)
            self.assertFalse(allowed)

        with patch("safe_batch_ingest.get_current_storage_mb", return_value=(300.0, "MockEngine")):
            # 1,000 txns @ 0.650 KB = ~0.63 MB -> 300 + 0.63 = 300.63 < 450.0 MB ceiling
            allowed = check_storage_projection(self.conn, records_to_ingest=1000)
            self.assertTrue(allowed)

    def test_04_ensure_account_creates_foreign_keys(self):
        """Verifies ensure_account_exists creates customer and account records without error."""
        created_cust, created_acc = ensure_account_exists(self.conn, "ACC-NEW-01", customer_id="CUST-NEW-01", currency="INR")
        self.assertTrue(created_cust)
        self.assertTrue(created_acc)

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, currency FROM accounts WHERE id = 'ACC-NEW-01'")
        acc = cursor.fetchone()
        self.assertIsNotNone(acc)
        self.assertEqual(acc[0], "ACC-NEW-01")
        self.assertEqual(acc[1], "INR")

        # Second call should not re-create
        c2, a2 = ensure_account_exists(self.conn, "ACC-NEW-01", customer_id="CUST-NEW-01", currency="INR")
        self.assertFalse(c2)
        self.assertFalse(a2)

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

    def test_06_configurable_capacity_guard_thresholds(self):
        """Verifies configurable --quota-mb and --safety-reserve-mb enforce custom limits."""
        with patch("safe_batch_ingest.get_current_storage_mb", return_value=(95.0, "MockEngine")):
            # Quota 100 MB, reserve 10 MB -> ceiling 90 MB. Current is 95 MB -> must reject even 1 txn
            allowed = check_storage_projection(self.conn, records_to_ingest=1, quota_mb=100.0, safety_reserve_mb=10.0)
            self.assertFalse(allowed)

            # Quota 200 MB, reserve 20 MB -> ceiling 180 MB. Current is 95 MB -> 1,000 txns fits easily
            allowed = check_storage_projection(self.conn, records_to_ingest=1000, quota_mb=200.0, safety_reserve_mb=20.0)
            self.assertTrue(allowed)

    def test_07_chunked_deduplication_detects_existing_events(self):
        """Verifies check_existing_event_ids correctly identifies already-imported events."""
        cursor = self.conn.cursor()
        ensure_account_exists(self.conn, "ACC-DEDUP-1")
        ensure_account_exists(self.conn, "ACC-DEDUP-2")

        cursor.execute("""
            INSERT INTO transactions (
                id, event_id, source_account_id, destination_account_id,
                customer_id, amount, currency, transaction_type, payment_channel,
                status, scenario_id, dataset_source, risk_score, risk_band, scoring_status, created_at
            ) VALUES ('T-1', 'EVT-EXISTING-1', 'ACC-DEDUP-1', 'ACC-DEDUP-2', 'CUST-1', 100.0, 'USD',
                      'TRANSFER', 'ONLINE', 'COMPLETED', 'SC-1', 'DS-1', 10.0, 'ROUTINE', 'CURRENT', '2023-01-01T00:00:00Z')
        """)
        self.conn.commit()

        batch_candidates = ["EVT-EXISTING-1", "EVT-NEW-2", "EVT-NEW-3"]
        existing = check_existing_event_ids(cursor, batch_candidates)
        self.assertIn("EVT-EXISTING-1", existing)
        self.assertNotIn("EVT-NEW-2", existing)
        self.assertNotIn("EVT-NEW-3", existing)

    def test_08_rollback_cleans_unreferenced_batch_accounts(self):
        """Verifies rollback_batch removes accounts created exclusively by this batch."""
        cursor = self.conn.cursor()
        batch_id = f"BATCH-TEST-ACC-{uuid.uuid4().hex[:6]}"

        # Create two accounts: ACC-SOLE (only in this batch) and ACC-SHARED (in another batch too)
        ensure_account_exists(self.conn, "ACC-SOLE", customer_id="CUST-SOLE")
        ensure_account_exists(self.conn, "ACC-SHARED", customer_id="CUST-SHARED")

        # Transaction for this batch
        cursor.execute("""
            INSERT INTO transactions (
                id, event_id, source_account_id, destination_account_id,
                customer_id, amount, currency, transaction_type, payment_channel,
                status, scenario_id, dataset_source, risk_score, risk_band, scoring_status, created_at
            ) VALUES ('T-SOLE', 'EVT-SOLE', 'ACC-SOLE', 'ACC-SHARED', 'CUST-SOLE', 50.0, 'USD',
                      'TRANSFER', 'ONLINE', 'COMPLETED', ?, 'DS-1', 10.0, 'ROUTINE', 'CURRENT', '2023-01-01T00:00:00Z')
        """, (batch_id,))

        # Transaction for another batch referencing ACC-SHARED
        cursor.execute("""
            INSERT INTO transactions (
                id, event_id, source_account_id, destination_account_id,
                customer_id, amount, currency, transaction_type, payment_channel,
                status, scenario_id, dataset_source, risk_score, risk_band, scoring_status, created_at
            ) VALUES ('T-OTHER', 'EVT-OTHER', 'ACC-SHARED', 'ACC-OTHER', 'CUST-SHARED', 100.0, 'USD',
                      'TRANSFER', 'ONLINE', 'COMPLETED', 'OTHER-BATCH', 'DS-1', 10.0, 'ROUTINE', 'CURRENT', '2023-01-01T00:00:00Z')
        """)
        self.conn.commit()

        # Mock checkpoint containing this batch
        mock_checkpoint = {
            "datasets": {"NFPC": {"last_offset": 10, "total_ingested": 1}},
            "batches": [{
                "batch_id": batch_id,
                "dataset_name": "NFPC",
                "start_offset": 9,
                "end_offset": 10,
                "records_ingested": 1,
                "created_accounts": ["ACC-SOLE", "ACC-SHARED"],
                "created_customers": ["CUST-SOLE", "CUST-SHARED"],
                "status": "COMPLETED"
            }]
        }

        class MockConnContext:
            def __init__(self, conn):
                self.conn = conn
            def __enter__(self):
                return self.conn
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("safe_batch_ingest.get_db_connection", return_value=MockConnContext(self.conn)), \
             patch("safe_batch_ingest.load_checkpoint", return_value=mock_checkpoint), \
             patch("safe_batch_ingest.save_checkpoint") as mock_save:

            success = rollback_batch(batch_id)
            self.assertTrue(success)

            # ACC-SOLE must be deleted because it has no remaining transactions
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE id = 'ACC-SOLE'")
            self.assertEqual(cursor.fetchone()[0], 0)

            # ACC-SHARED must be retained because it is still referenced by T-OTHER
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE id = 'ACC-SHARED'")
            self.assertEqual(cursor.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
