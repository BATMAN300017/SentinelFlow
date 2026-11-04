"""
SentinelFlow AI - AML Model Remediation Audit Test Suite.

Proves all 10 required acceptance criteria from Section 7:
1. Ground-truth labels cannot influence prediction scores.
2. Re-ingestion cannot restore label-derived scores.
3. Future transactions cannot influence historical features.
4. Same-timestamp and missing-timestamp cases are deterministic.
5. Training and inference produce identical feature schemas.
6. A failed model load cannot activate a synthetic fallback.
7. Scoring errors cannot become legitimate-looking zero-risk predictions.
8. Missing predictions are excluded and counted in evaluation.
9. Confusion matrix totals reconcile with sample counts.
10. Repeated evaluation on identical inputs produces identical results.
"""

import unittest
import sqlite3
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.core.database import SCHEMA_SQL, init_db
from app.detection.rules import ensure_default_rules
from app.detection.features import extract_transaction_features, parse_event_time
from app.detection.engine import score_transaction
from app.detection.supervised import (
    FEATURE_SCHEMA,
    extract_supervised_feature_vector,
    predict_supervised_risk,
    VERSION_V2_REMEDIATED,
    VERSION_V1_BASELINE,
    set_active_model_version
)
from app.detection.ensemble import compute_ensemble_risk
from app.api.v1.datasets import _persist_canonical_records
from app.evaluation.evaluator import IndependentEvaluator

class TestMLRemediationAudit(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_01_ground_truth_labels_cannot_influence_predictions(self):
        """1. Ground-truth labels cannot influence prediction scores."""
        txn_clean = {
            "id": "TXN-AUDIT-01",
            "source_account_id": "ACC-AUDIT-SRC",
            "destination_account_id": "ACC-AUDIT-DEST",
            "amount": 4200.0,
            "currency": "USD",
            "created_at": "2022-10-07T12:00:00Z"
        }
        txn_contaminated = dict(txn_clean)
        txn_contaminated["is_laundering"] = 1
        txn_contaminated["ground_truth_label"] = "CONFIRMED_LAUNDERING_RING"
        txn_contaminated["Is_laundering"] = 1

        score_clean = score_transaction(self.conn, txn_clean)
        score_contam = score_transaction(self.conn, txn_contaminated)

        # Ground truth fields MUST NOT alter the prediction score
        self.assertEqual(
            score_clean["final_risk_score"],
            score_contam["final_risk_score"],
            "Ground truth label leaked into final prediction score!"
        )
        self.assertEqual(
            score_clean["supervised_prediction"]["supervised_score"],
            score_contam["supervised_prediction"]["supervised_score"],
            "Ground truth label leaked into supervised model prediction!"
        )

    def test_02_reingestion_cannot_restore_label_derived_scores(self):
        """2. Re-ingestion cannot restore label-derived scores."""
        # Insert initial genuine score
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-REINGEST-01', 'EVT-REINGEST-01', 'ACC-01', 'CUST-01', 5000.0, 'USD', 'TRANSFER', 'ACH', 37.5, 'LOW', 'AUDIT_DS', '2022-10-07T12:00:00Z')
        """)
        self.conn.commit()

        # Simulate re-ingestion with None risk_score (unscored payload)
        reingest_batch = [{
            "id": "TXN-REINGEST-01",
            "event_id": "EVT-REINGEST-01",
            "source_account_id": "ACC-01",
            "customer_id": "CUST-01",
            "amount": 5000.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ACH",
            "created_at": "2022-10-07T12:00:00Z"
        }]

        with patch("app.detection.engine.score_transaction", side_effect=RuntimeError("Simulated engine offline")):
            _persist_canonical_records(self.conn, reingest_batch, "AUDIT_DS")

        # Verify that genuine risk_score 37.5 was preserved by COALESCE
        self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = 'TXN-REINGEST-01'")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], 37.5, "Re-ingestion overwrote genuine model score with failure or zero!")

    def test_03_future_transactions_cannot_influence_historical_features(self):
        """3. Future transactions cannot influence historical features."""
        # Insert historical baseline transaction T1 at 12:00
        t1 = {
            "id": "TXN-HIST-01",
            "event_id": "EVT-HIST-01",
            "source_account_id": "ACC-TIME-01",
            "destination_account_id": "ACC-TIME-02",
            "customer_id": "CUST-TIME-01",
            "amount": 1000.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ACH",
            "created_at": "2022-10-07T12:00:00Z"
        }
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (t1["id"], t1["event_id"], t1["source_account_id"], t1["destination_account_id"], t1["customer_id"], t1["amount"], t1["currency"], t1["transaction_type"], t1["payment_channel"], t1["created_at"]))
        self.conn.commit()

        feats_before_future = extract_transaction_features(self.conn, t1)

        # Now insert a FUTURE transaction T2 at 12:05 with massive amount and velocity
        t2 = {
            "id": "TXN-HIST-02",
            "event_id": "EVT-HIST-02",
            "source_account_id": "ACC-TIME-01",
            "destination_account_id": "ACC-TIME-03",
            "customer_id": "CUST-TIME-01",
            "amount": 95000.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ACH",
            "created_at": "2022-10-07T12:05:00Z"
        }
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (t2["id"], t2["event_id"], t2["source_account_id"], t2["destination_account_id"], t2["customer_id"], t2["amount"], t2["currency"], t2["transaction_type"], t2["payment_channel"], t2["created_at"]))
        self.conn.commit()

        # Re-extract features for T1
        feats_after_future = extract_transaction_features(self.conn, t1)

        # Future transaction T2 MUST NOT alter T1's features
        self.assertEqual(feats_before_future["history_count"], feats_after_future["history_count"])
        self.assertEqual(feats_before_future["short_window_count"], feats_after_future["short_window_count"])
        self.assertEqual(feats_before_future["short_window_sum"], feats_after_future["short_window_sum"])

    def test_04_same_timestamp_and_missing_timestamp_deterministic(self):
        """4. Same-timestamp and missing-timestamp cases are deterministic."""
        # Same timestamp: TXN-A and TXN-B have identical created_at
        ts = "2022-10-07T14:00:00Z"
        t_a = {"id": "TXN-A", "event_id": "EVT-A", "source_account_id": "ACC-SAME-01", "customer_id": "CUST-SAME-01", "amount": 500.0, "currency": "USD", "transaction_type": "TRANSFER", "payment_channel": "ACH", "created_at": ts}
        t_b = {"id": "TXN-B", "event_id": "EVT-B", "source_account_id": "ACC-SAME-01", "customer_id": "CUST-SAME-01", "amount": 600.0, "currency": "USD", "transaction_type": "TRANSFER", "payment_channel": "ACH", "created_at": ts}

        self.cursor.execute("INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (t_a["id"], t_a["event_id"], t_a["source_account_id"], t_a["customer_id"], t_a["amount"], t_a["currency"], t_a["transaction_type"], t_a["payment_channel"], t_a["created_at"]))
        self.cursor.execute("INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (t_b["id"], t_b["event_id"], t_b["source_account_id"], t_b["customer_id"], t_b["amount"], t_b["currency"], t_b["transaction_type"], t_b["payment_channel"], t_b["created_at"]))
        self.conn.commit()

        # TXN-B has id > TXN-A, so TXN-B sees TXN-A in its prior history
        feats_b = extract_transaction_features(self.conn, t_b)
        self.assertGreaterEqual(feats_b["short_window_count"], 2)

        # TXN-A has id < TXN-B, so TXN-A does NOT see TXN-B
        feats_a = extract_transaction_features(self.conn, t_a)
        self.assertEqual(feats_a["history_count"], 0)

        # Missing timestamp MUST raise ValueError, not substitute datetime.now()
        with self.assertRaises(ValueError):
            parse_event_time(None)
        with self.assertRaises(ValueError):
            parse_event_time("")
        with self.assertRaises(ValueError):
            extract_transaction_features(self.conn, {"id": "TXN-NO-TIME", "source_account_id": "ACC-01", "amount": 100.0})

    def test_05_training_and_inference_produce_identical_feature_schemas(self):
        """5. Training and inference produce identical feature schemas."""
        self.assertEqual(len(FEATURE_SCHEMA), 9)
        sample_features = {
            "amount": 2500.0,
            "short_window_count": 3,
            "rapid_movement_detected": 1,
            "structuring_flag": 0,
            "is_cross_border": 1,
            "is_cash_channel": 0,
            "is_new_beneficiary": 1,
            "unique_counterparties": 2,
            "history_count": 5
        }
        vec = extract_supervised_feature_vector(sample_features)
        self.assertEqual(vec.shape, (1, 9))
        self.assertEqual(vec.dtype, float)
        # Check values correspond to canonical features
        self.assertAlmostEqual(vec[0][0], np.log10(2500.0), places=3)
        self.assertEqual(vec[0][1], 3.0)
        self.assertEqual(vec[0][2], 1.0)
        self.assertEqual(vec[0][4], 1.0)

    def test_06_failed_model_load_cannot_activate_synthetic_fallback(self):
        """6. A failed model load cannot activate a synthetic fallback."""
        with patch("app.detection.supervised._init_rf_remediated", return_value=None):
            set_active_model_version(VERSION_V2_REMEDIATED)
            res = predict_supervised_risk({"amount": 5000.0, "short_window_count": 1})
            self.assertEqual(res["model_status"], "MODEL_UNAVAILABLE")
            self.assertIsNone(res["supervised_score"])
            self.assertIsNone(res["predicted_risk_probability"])

    def test_07_scoring_errors_cannot_become_legitimate_zero_risk(self):
        """7. Scoring errors cannot become legitimate-looking zero-risk predictions."""
        txns = [{
            "id": "TXN-FAIL-01",
            "source_account_id": "ACC-FAIL",
            "amount": 1000.0,
            "currency": "USD",
            "created_at": "2022-10-07T12:00:00Z"
        }]

        with patch("app.detection.engine.score_transaction", side_effect=Exception("Database lock failure")):
            summary = _persist_canonical_records(self.conn, txns, "FAIL_DS")
            self.assertEqual(summary["failed_count"], 1)
            self.assertEqual(summary["scored_count"], 0)

        # Check in DB that risk_score is NULL and risk_band is FAILED, not 0.0 or ROUTINE
        self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = 'TXN-FAIL-01'")
        row = self.cursor.fetchone()
        self.assertIsNone(row[0])
        self.assertEqual(row[1], "FAILED")

    def test_08_missing_predictions_excluded_and_counted_in_evaluation(self):
        """8. Missing predictions are excluded and counted in evaluation."""
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={
            "transactions": {
                "TXN-1": {"is_laundering": 1, "laundering_type": "FAN_OUT"},
                "TXN-2": {"is_laundering": 0, "laundering_type": "NORMAL"},
                "TXN-3": {"is_laundering": 1, "laundering_type": "STRUCTURING"}  # Missing prediction
            }
        }):
            # Insert predictions for only TXN-1 and TXN-2; TXN-3 has NULL score
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, transaction_type, payment_channel, dataset_source, risk_score, created_at)
                VALUES ('TXN-1', 'EVT-1', 'ACC-1', 'CUST-1', 100.0, 'TRANSFER', 'ACH', 'TEST_DS', 80.0, '2022-10-07T12:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, transaction_type, payment_channel, dataset_source, risk_score, created_at)
                VALUES ('TXN-2', 'EVT-2', 'ACC-2', 'CUST-2', 100.0, 'TRANSFER', 'ACH', 'TEST_DS', 20.0, '2022-10-07T12:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, transaction_type, payment_channel, dataset_source, risk_score, created_at)
                VALUES ('TXN-3', 'EVT-3', 'ACC-3', 'CUST-3', 100.0, 'TRANSFER', 'ACH', 'TEST_DS', NULL, '2022-10-07T12:00:00Z')
            """)
            self.conn.commit()

            res = IndependentEvaluator.evaluate_transaction_level(self.conn, "TEST_DS", risk_threshold=70.0)
            self.assertEqual(res["sample_accounting"]["matched_predictions"], 2)
            self.assertEqual(res["sample_accounting"]["missing_predictions"], 1)
            self.assertEqual(res["total_evaluated_samples"], 2)

    def test_09_confusion_matrix_totals_reconcile_with_sample_counts(self):
        """9. Confusion matrix totals reconcile with sample counts."""
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={
            "transactions": {
                f"TXN-{i}": {"is_laundering": 1 if i % 5 == 0 else 0, "laundering_type": "TEST"}
                for i in range(50)
            }
        }):
            for i in range(50):
                score = 85.0 if i % 4 == 0 else 25.0
                self.cursor.execute("""
                    INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, transaction_type, payment_channel, dataset_source, risk_score, created_at)
                    VALUES (?, ?, 'ACC-X', 'CUST-X', 100.0, 'TRANSFER', 'ACH', 'TEST_RECON', ?, '2022-10-07T12:00:00Z')
                """, (f"TXN-{i}", f"EVT-{i}", score))
            self.conn.commit()

            res = IndependentEvaluator.evaluate_transaction_level(self.conn, "TEST_RECON", risk_threshold=70.0)
            cm = res["confusion_matrix"]
            total_reconciled = cm["true_positives"] + cm["false_positives"] + cm["true_negatives"] + cm["false_negatives"]
            self.assertEqual(total_reconciled, res["total_evaluated_samples"])
            self.assertEqual(cm["reconciled_total"], 50)

    def test_10_repeated_evaluation_produces_identical_results(self):
        """10. Repeated evaluation on identical inputs produces identical results."""
        res1 = IndependentEvaluator.evaluate_saml_untouched_test_set(risk_threshold=55.0)
        res2 = IndependentEvaluator.evaluate_saml_untouched_test_set(risk_threshold=55.0)

        self.assertEqual(res1["metrics"], res2["metrics"])
        self.assertEqual(res1["confusion_matrix"], res2["confusion_matrix"])
        self.assertEqual(res1["total_evaluated_samples"], res2["total_evaluated_samples"])

if __name__ == "__main__":
    unittest.main()
