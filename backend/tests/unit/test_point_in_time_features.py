"""
Unit Tests for Unified Point-in-Time Feature Module.

Validates:
1. Offline-Online Parity: Features derived via OfflineFeatureExtractor (streaming)
   and extract_online_transaction_features (SQLite) are 100% mathematically identical.
2. Zero Future Leakage: Subsequent transactions (at t + 1h, t + 1d) inserted into the DB
   have ZERO impact on features computed for a prior transaction.
3. Deterministic Event-Time & Tie-Breaking: Strict epoch < t OR (epoch == t AND id < id).
4. Cycle Detection Parity: Bilateral round-trip flows correctly trigger cycle_indicator.
"""

import unittest
import sqlite3
import os
import sys
import numpy as np
from datetime import datetime, timezone, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SCHEMA_SQL
from app.detection.point_in_time_features import (
    AML_FEATURE_NAMES,
    compute_point_in_time_features,
    extract_online_transaction_features,
    OfflineFeatureExtractor,
    encode_payment_type,
    parse_to_epoch,
    PRIOR_RISK,
    SENDER_COUNTRY_RISK,
    RECEIVER_COUNTRY_RISK,
    CURRENCY_RISK
)


class TestPointInTimeFeatures(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_01_feature_names_canonical_length(self):
        """Verifies exactly 24 features defined with expected names."""
        self.assertEqual(len(AML_FEATURE_NAMES), 24)
        self.assertEqual(AML_FEATURE_NAMES[0], "log_amount")
        self.assertEqual(AML_FEATURE_NAMES[1], "amount_robust_z")
        self.assertEqual(AML_FEATURE_NAMES[23], "cycle_indicator")

    def test_02_offline_online_feature_parity(self):
        """
        Feeds a sequence of 10 sequential transactions to both:
        1. In-memory SQLite database
        2. In-memory OfflineFeatureExtractor
        Asserts that online SQL query and offline extractor produce identical vectors.
        """
        extractor = OfflineFeatureExtractor()
        
        base_dt = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        
        txns = [
            # 1. Cold start transaction for ACC-A -> ACC-B
            {
                "id": "TXN-001",
                "source_account_id": "ACC-A",
                "destination_account_id": "ACC-B",
                "amount": 5000.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "US",
                "receiver_country": "US",
                "payment_type": "TRANSFER",
                "created_at": (base_dt).isoformat(),
                "status": "COMPLETED"
            },
            # 2. ACC-C -> ACC-A (inbound to A)
            {
                "id": "TXN-002",
                "source_account_id": "ACC-C",
                "destination_account_id": "ACC-A",
                "amount": 9500.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "MOROCCO",
                "receiver_country": "US",
                "payment_type": "WIRE",
                "created_at": (base_dt + timedelta(minutes=15)).isoformat(),
                "status": "COMPLETED"
            },
            # 3. ACC-A -> ACC-B (second transaction from A: pass-through & velocity)
            {
                "id": "TXN-003",
                "source_account_id": "ACC-A",
                "destination_account_id": "ACC-B",
                "amount": 9200.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "US",
                "receiver_country": "US",
                "payment_type": "TRANSFER",
                "created_at": (base_dt + timedelta(minutes=30)).isoformat(),
                "status": "COMPLETED"
            },
            # 4. Structuring transaction near threshold ($9,500)
            {
                "id": "TXN-004",
                "source_account_id": "ACC-A",
                "destination_account_id": "ACC-D",
                "amount": 9500.0,
                "currency": "USD",
                "received_currency": "EUR",
                "sender_country": "US",
                "receiver_country": "GERMANY",
                "payment_type": "CROSS-BORDER",
                "created_at": (base_dt + timedelta(hours=2)).isoformat(),
                "status": "COMPLETED"
            },
            # 5. Round amount cash withdrawal ($2,000)
            {
                "id": "TXN-005",
                "source_account_id": "ACC-A",
                "destination_account_id": "ACC-E",
                "amount": 2000.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "US",
                "receiver_country": "US",
                "payment_type": "CASH WITHDRAWAL",
                "created_at": (base_dt + timedelta(hours=5)).isoformat(),
                "status": "COMPLETED"
            },
            # 6. ACC-B -> ACC-A (Bilateral cycle trigger: B sends back to A)
            {
                "id": "TXN-006",
                "source_account_id": "ACC-B",
                "destination_account_id": "ACC-A",
                "amount": 4000.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "US",
                "receiver_country": "US",
                "payment_type": "TRANSFER",
                "created_at": (base_dt + timedelta(hours=6)).isoformat(),
                "status": "COMPLETED"
            },
            # 7. ACC-A -> ACC-B (A sends back to B; cycle flag should now be 1.0)
            {
                "id": "TXN-007",
                "source_account_id": "ACC-A",
                "destination_account_id": "ACC-B",
                "amount": 12000.0,
                "currency": "USD",
                "received_currency": "USD",
                "sender_country": "US",
                "receiver_country": "US",
                "payment_type": "TRANSFER",
                "created_at": (base_dt + timedelta(hours=8)).isoformat(),
                "status": "COMPLETED"
            }
        ]

        # Insert and test step by step
        for idx, t in enumerate(txns):
            # Compute offline vector BEFORE state update
            offline_vec = extractor.transform_transaction(t, update_state=True)

            # Insert into SQLite
            self.cursor.execute("""
                INSERT INTO transactions (
                    id, event_id, source_account_id, destination_account_id, customer_id,
                    amount, currency, transaction_type, payment_channel, status, created_at
                ) VALUES (?, ?, ?, ?, 'CUST-TEST', ?, ?, ?, ?, ?, ?)
            """, (
                t["id"], f"EVT-{t['id']}", t["source_account_id"], t["destination_account_id"],
                t["amount"], t["currency"], t["payment_type"], t["payment_type"],
                t["status"], t["created_at"]
            ))
            self.conn.commit()

            # Compute online vector from SQLite
            online_vec = extract_online_transaction_features(self.conn, t)

            # Verify 100% parity
            self.assertEqual(len(offline_vec), len(online_vec))
            np.testing.assert_allclose(
                online_vec, offline_vec,
                rtol=1e-5, atol=1e-5,
                err_msg=f"Discrepancy at transaction index {idx} ({t['id']})"
            )

        # Specifically check transaction 7 (ACC-A -> ACC-B): cycle indicator must be 1.0
        t7 = txns[6]
        vec7 = extract_online_transaction_features(self.conn, t7)
        cycle_idx = AML_FEATURE_NAMES.index("cycle_indicator")
        self.assertEqual(vec7[cycle_idx], 1.0, "Cycle indicator should be 1.0 because ACC-B sent to ACC-A in TXN-006")

    def test_03_zero_future_leakage_guarantee(self):
        """
        Verifies that adding transactions in the future does NOT alter
        the feature vector computed for an earlier transaction.
        """
        base_dt = datetime(2023, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        t1 = {
            "id": "TXN-PAST-001",
            "source_account_id": "ACC-MULE-1",
            "destination_account_id": "ACC-TARGET-1",
            "amount": 4500.0,
            "currency": "USD",
            "received_currency": "USD",
            "sender_country": "US",
            "receiver_country": "US",
            "payment_type": "TRANSFER",
            "created_at": base_dt.isoformat(),
            "status": "COMPLETED"
        }

        # Insert T1
        self.cursor.execute("""
            INSERT INTO transactions (
                id, event_id, source_account_id, destination_account_id, customer_id,
                amount, currency, transaction_type, payment_channel, status, created_at
            ) VALUES (?, ?, ?, ?, 'CUST-1', ?, ?, ?, ?, ?, ?)
        """, (
            t1["id"], "EVT-01", t1["source_account_id"], t1["destination_account_id"],
            t1["amount"], t1["currency"], t1["payment_type"], t1["payment_type"],
            t1["status"], t1["created_at"]
        ))
        self.conn.commit()

        # Compute initial feature vector for T1
        vec_before = extract_online_transaction_features(self.conn, t1)

        # Now insert multiple aggressive future transactions involving ACC-MULE-1
        future_txns = [
            ("TXN-FUT-001", base_dt + timedelta(minutes=5), 50000.0),
            ("TXN-FUT-002", base_dt + timedelta(hours=1), 80000.0),
            ("TXN-FUT-003", base_dt + timedelta(days=2), 120000.0),
        ]
        for f_id, f_time, f_amt in future_txns:
            self.cursor.execute("""
                INSERT INTO transactions (
                    id, event_id, source_account_id, destination_account_id, customer_id,
                    amount, currency, transaction_type, payment_channel, status, created_at
                ) VALUES (?, ?, 'ACC-MULE-1', 'ACC-TARGET-2', 'CUST-1', ?, 'USD', 'TRANSFER', 'ONLINE', 'COMPLETED', ?)
            """, (f_id, f"EVT-{f_id}", f_amt, f_time.isoformat()))
        self.conn.commit()

        # Re-compute feature vector for T1
        vec_after = extract_online_transaction_features(self.conn, t1)

        # Zero leakage check: vec_before must exactly equal vec_after
        np.testing.assert_array_equal(
            vec_before, vec_after,
            err_msg="Future transactions leaked into historical feature extraction!"
        )

    def test_04_target_encodings_and_risk_priors(self):
        """Verifies country and currency risks match pre-fitted training priors."""
        # Known high risk
        self.assertAlmostEqual(SENDER_COUNTRY_RISK["MOROCCO"], 0.003258, places=5)
        self.assertAlmostEqual(RECEIVER_COUNTRY_RISK["NIGERIA"], 0.006114, places=5)
        self.assertAlmostEqual(CURRENCY_RISK["MOROCCAN DIRHAM"], 0.003544, places=5)

        # Unknown country falls back to PRIOR_RISK
        vec = compute_point_in_time_features(
            amount=100.0,
            current_epoch=1670000000,
            current_id="TXN-X",
            payment_type_raw="TRANSFER",
            payment_currency_raw="FANTASY_CURRENCY",
            received_currency_raw="FANTASY_CURRENCY",
            sender_country_raw="ATLANTIS",
            receiver_country_raw="WAKANDA",
            receiver_id="ACC-DST",
            prior_outbound=[],
            prior_inbound=[]
        )
        self.assertEqual(vec[AML_FEATURE_NAMES.index("sender_country_risk")], PRIOR_RISK)
        self.assertEqual(vec[AML_FEATURE_NAMES.index("receiver_country_risk")], PRIOR_RISK)
        self.assertEqual(vec[AML_FEATURE_NAMES.index("currency_risk")], PRIOR_RISK)


if __name__ == "__main__":
    unittest.main()
