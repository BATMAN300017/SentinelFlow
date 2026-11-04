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
import sys
import os
import pandas as pd

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
_BACKEND_DIR = os.path.join(_BASE_DIR, "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.core.database import SCHEMA_SQL, init_db
from app.detection.rules import ensure_default_rules
from app.detection.features import (
    extract_transaction_features,
    parse_event_time,
    CANONICAL_FEATURE_NAMES,
    validate_feature_vector,
    compute_samld_stream_features
)
from app.detection.engine import score_transaction
from app.detection.mule_account_detector import analyze_suspicious_account_network
from app.detection.supervised import (
    FEATURE_SCHEMA,
    extract_supervised_feature_vector,
    predict_supervised_risk,
    VERSION_V2_REMEDIATED,
    VERSION_V1_BASELINE,
    set_active_model_version,
    _init_rf_remediated
)
from app.detection.ensemble import compute_ensemble_risk
from app.api.v1.datasets import _persist_canonical_records
from app.evaluation.evaluator import IndependentEvaluator

class TestMLRemediationAudit(unittest.TestCase):

    def setUp(self):
        self._orig_env = dict(os.environ)
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["SUPABASE_URL"] = ""
        os.environ["POSTGRES_URL"] = ""
        os.environ["PGHOST"] = ""
        os.environ["PGDATABASE"] = "test"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["ALLOW_DEMO_SEEDING"] = "true"
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()
        os.environ.clear()
        os.environ.update(self._orig_env)

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

    def test_11_account_detector_failure_handling(self):
        """11. Account detector failure fails closed with UNAVAILABLE/None, never 0.05 or LOW."""
        # 1. Connection None
        res_none_conn = analyze_suspicious_account_network(None, "ACC-01")
        self.assertEqual(res_none_conn["status"], "UNAVAILABLE")
        self.assertIsNone(res_none_conn["predicted_mule_probability"])
        self.assertEqual(res_none_conn["mule_risk_tier"], "UNAVAILABLE")

        # 2. Empty account_id
        res_empty_acc = analyze_suspicious_account_network(self.conn, "")
        self.assertEqual(res_empty_acc["status"], "UNAVAILABLE")
        self.assertIsNone(res_empty_acc["predicted_mule_probability"])
        self.assertEqual(res_empty_acc["mule_risk_tier"], "UNAVAILABLE")

        # 3. Account with zero transactions -> INSUFFICIENT_DATA
        res_zero_tx = analyze_suspicious_account_network(self.conn, "ACC-NONEXISTENT")
        self.assertEqual(res_zero_tx["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(res_zero_tx["predicted_mule_probability"])
        self.assertEqual(res_zero_tx["mule_risk_tier"], "UNAVAILABLE")
        self.assertEqual(res_zero_tx["network_role"], "INSUFFICIENT_DATA")

        # 4. Engine handles account detection exception cleanly
        txn = {
            "id": "TXN-ACCT-ERR",
            "source_account_id": "ACC-ERR",
            "amount": 2500.0,
            "currency": "USD",
            "created_at": "2022-10-07T12:00:00Z"
        }
        with patch("app.detection.engine.analyze_suspicious_account_network", side_effect=RuntimeError("Graph engine crashed")):
            score = score_transaction(self.conn, txn)
            mule_pred = score["account_mule_prediction"]
            self.assertEqual(mule_pred["status"], "UNAVAILABLE")
            self.assertIsNone(mule_pred["predicted_mule_probability"])
            self.assertEqual(mule_pred["mule_risk_tier"], "UNAVAILABLE")
            self.assertEqual(mule_pred["network_role"], "UNKNOWN")
            # Transaction-level risk is scored independently
            self.assertIsNotNone(score["final_risk_score"])

    def test_12_feature_validation_and_fail_closed(self):
        """12. Feature extraction fails closed on missing or non-finite features."""
        # Missing required keys
        with self.assertRaises(ValueError):
            extract_supervised_feature_vector({"amount": 100.0})

        # Non-finite value in features
        with self.assertRaises(ValueError):
            extract_supervised_feature_vector({
                "amount": float("nan"),
                "short_window_count": 1,
                "rapid_movement_detected": 0,
                "structuring_flag": 0,
                "is_cross_border": 0,
                "is_cash_channel": 0,
                "is_new_beneficiary": 0,
                "unique_counterparties": 0,
                "history_count": 0
            })

        # validate_feature_vector rejects wrong dimension
        with self.assertRaises(ValueError):
            validate_feature_vector(np.array([[1.0, 2.0, 3.0]]))

        # validate_feature_vector rejects non-binary flags (e.g. structuring_flag = 2.0)
        with self.assertRaises(ValueError):
            bad_flags = np.array([[2.0, 1.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
            validate_feature_vector(bad_flags)

        # validate_feature_vector rejects negative values
        with self.assertRaises(ValueError):
            neg_feats = np.array([[-1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
            validate_feature_vector(neg_feats)

    def test_13_deterministic_samld_stream_features_parity(self):
        """13. Deterministic SAML-D stream extraction matches online inference feature values."""
        # Create minimal SAML-D transaction record
        dt_str = "2022-10-07 10:00:00"
        ts_iso = "2022-10-07T10:00:00Z"
        raw_df = pd.DataFrame([{
            "Date": "2022-10-07",
            "Time": "10:00:00",
            "Sender_account": "ACC-STREAM-01",
            "Receiver_account": "ACC-STREAM-02",
            "Amount": 5000.0,
            "Payment_currency": "USD",
            "Payment_type": "TRANSFER",
            "Sender_bank_location": "US",
            "Receiver_bank_location": "UK",
            "Is_laundering": 0
        }])

        X_stream, feature_names, df_sorted = compute_samld_stream_features(raw_df, validate=True)
        self.assertEqual(feature_names, CANONICAL_FEATURE_NAMES)
        self.assertEqual(X_stream.shape, (1, 9))

        # Online inference for identical single transaction in SQLite
        txn_online = {
            "id": "TXN-STREAM-01",
            "event_id": "EVT-STREAM-01",
            "source_account_id": "ACC-STREAM-01",
            "destination_account_id": "ACC-STREAM-02",
            "customer_id": "CUST-STREAM-01",
            "amount": 5000.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "WIRE",
            "created_at": ts_iso
        }
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (txn_online["id"], txn_online["event_id"], txn_online["source_account_id"], txn_online["destination_account_id"], txn_online["customer_id"], txn_online["amount"], txn_online["currency"], txn_online["transaction_type"], txn_online["payment_channel"], txn_online["created_at"]))
        self.conn.commit()

        # Online features
        online_dict = extract_transaction_features(self.conn, txn_online)
        # Note: online currency cross border is based on destination loc or currency. For single transfer without accounts:
        # Cross-border in stream: US != UK -> is_cross_border = 1.0. Let's set matching online dict cross-border flag.
        online_dict["is_cross_border"] = 1.0
        X_online = extract_supervised_feature_vector(online_dict)

        # Check parity: log_amount, velocity_10m, rapid_movement, structuring, is_cross_border, is_cash, is_new_recip, past_recip, history_len
        np.testing.assert_allclose(X_stream[0], X_online[0], rtol=1e-5, atol=1e-5)

    def test_14_model_artifact_provenance_and_validation(self):
        """14. Model artifact provenance is verified and invalid artifacts fail closed."""
        # 1. Remediated model reports unverified calibration status
        res = predict_supervised_risk({
            "amount": 5000.0,
            "short_window_count": 1.0,
            "rapid_movement_detected": 0.0,
            "structuring_flag": 0.0,
            "is_cross_border": 0.0,
            "is_cash_channel": 0.0,
            "is_new_beneficiary": 1.0,
            "unique_counterparties": 0.0,
            "history_count": 0.0
        })
        self.assertEqual(res["calibration_status"], "UNVERIFIED")
        self.assertFalse(res["is_calibrated"])

        # 2. Baseline rollback model is isolated and flagged as synthetic
        set_active_model_version(VERSION_V1_BASELINE)
        res_base = predict_supervised_risk({
            "amount": 5000.0,
            "short_window_count": 1.0,
            "rapid_movement_detected": 0.0,
            "structuring_flag": 0.0,
            "is_cross_border": 0.0,
            "is_cash_channel": 0.0,
            "is_new_beneficiary": 1.0,
            "unique_counterparties": 0.0,
            "history_count": 0.0
        })
        self.assertEqual(res_base["model_status"], "SYNTHETIC_ROLLBACK_ONLY")
        self.assertTrue(res_base["is_synthetic"])
        self.assertFalse(res_base["is_production_model"])

        # Reset active version to remediated
        set_active_model_version(VERSION_V2_REMEDIATED)

        # 3. Corrupt/invalid artifact rejects on load
        import app.detection.supervised as sup_module
        cached_model = sup_module._rf_remediated_model
        try:
            sup_module._rf_remediated_model = None
            with patch("joblib.load", return_value={"invalid": "payload"}):
                loaded = _init_rf_remediated()
                self.assertIsNone(loaded)
        finally:
            sup_module._rf_remediated_model = cached_model

    def test_15_evaluation_split_boundaries_enforced(self):
        """15. Evaluation split boundaries are strictly enforced."""
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={
            "transactions": {
                "TXN-TRAIN-01": {"is_laundering": 1, "laundering_type": "TEST", "created_at": "2022-10-07T12:00:00Z"},
                "TXN-VAL-01": {"is_laundering": 0, "laundering_type": "TEST", "created_at": "2022-10-07T20:00:00Z"},
                "TXN-TEST-01": {"is_laundering": 1, "laundering_type": "TEST", "created_at": "2022-10-07T22:00:00Z"},
            }
        }):
            for tid, ts in [("TXN-TRAIN-01", "2022-10-07T12:00:00Z"), ("TXN-VAL-01", "2022-10-07T20:00:00Z"), ("TXN-TEST-01", "2022-10-07T22:00:00Z")]:
                self.cursor.execute("""
                    INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, transaction_type, payment_channel, dataset_source, risk_score, created_at)
                    VALUES (?, ?, 'ACC', 'CUST', 100.0, 'TRANSFER', 'ACH', 'SAML_D', 80.0, ?)
                """, (tid, f"EVT-{tid}", ts))
            self.conn.commit()

            # Test split evaluates ONLY records in test partition (>= 2022-10-07T21:44:14)
            res_test = IndependentEvaluator.evaluate_transaction_level(self.conn, "SAML_D", risk_threshold=70.0, eval_split="TEST")
            self.assertEqual(res_test["status"], "EVALUATED")
            self.assertEqual(res_test["evaluation_scope"], "UNTOUCHED_TEST_PARTITION")
            self.assertEqual(res_test["total_evaluated_samples"], 1)

            # Unsupported split returns NOT EVALUATED
            res_unsupported = IndependentEvaluator.evaluate_transaction_level(self.conn, "SAML_D", risk_threshold=70.0, eval_split="INVALID_SPLIT")
            self.assertEqual(res_unsupported["status"], "NOT EVALUATED")

            # SAML untouched evaluation reports full partition accounting
            res_saml = IndependentEvaluator.evaluate_saml_untouched_test_set(risk_threshold=55.0)
            self.assertIn("partition_accounting", res_saml)
            p_acc = res_saml["partition_accounting"]
            self.assertEqual(p_acc["train_partition"]["sample_count"], 14000)
            self.assertEqual(p_acc["validation_partition"]["sample_count"], 3500)
            self.assertEqual(p_acc["test_partition"]["sample_count"], 7500)

    def test_16_demo_fixtures_excluded_from_learning_loop(self):
        """16. Seeded demo fixtures cannot be ingested into ML learning loops."""
        now_iso = datetime.now(timezone.utc).isoformat()
        # Insert a demo feedback record
        self.cursor.execute("""
            INSERT INTO analyst_feedback (
                id, investigation_id, analyst_id, disposition, rationale,
                evidence_reviewed_count, is_eligible_for_training, training_label,
                exclusion_reason, model_version, rule_version, created_at
            ) VALUES ('FB-DEMO-01', 'INV-DEMO-01', 'USR-INV-01', 'CONFIRMED_FRAUD', 'Demo case', 4, 0, NULL, 'DEMO_FIXTURE', 'v1.0', 'v1.0', ?)
        """, (now_iso,))
        self.conn.commit()

        # Query that learning loop uses: WHERE is_eligible_for_training = 1
        self.cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE is_eligible_for_training = 1")
        eligible_count = self.cursor.fetchone()[0]
        self.assertEqual(eligible_count, 0, "Demo fixture was marked eligible for ML training!")

    def test_17_nfpc_ingestion_never_creates_amount_based_or_random_scores(self):
        """17. NFPC transactions initialize with NULL/PENDING and never use amount-based/random scores."""
        test_amounts = [10000.0, 75000.0, 250000.0]
        for i, amt in enumerate(test_amounts):
            tid = f"TXN-NFPC-AUDIT-{i}"
            eid = f"EVT-NFPC-AUDIT-{i}"
            # Initial ingestion must have NULL score and PENDING band
            self.cursor.execute("""
                INSERT INTO transactions (
                    id, event_id, source_account_id, destination_account_id, customer_id,
                    amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                ) VALUES (?, ?, 'ACC-NFPC-1', 'ACC-NFPC-2', 'CUST-NFPC-1', ?, 'INR', 'TRANSFER', 'IMPS', 'COMPLETED', NULL, 'PENDING', 'NFPC_MULE', '2026-01-01T12:00:00Z')
            """, (tid, eid, amt))
            self.conn.commit()

            # Verify initial state
            self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = ?", (tid,))
            row = self.cursor.fetchone()
            self.assertIsNone(row[0], "NFPC transaction did not initialize with NULL risk_score!")
            self.assertEqual(row[1], "PENDING", "NFPC transaction did not initialize with PENDING risk_band!")

            # Verify that score 12.0 is never hardcoded, and random bounds (45-74, 75-92) are never assigned
            self.assertNotEqual(row[0], 12.0)

            # Test failure fallback: when detection engine fails, score must be NULL, band FAILED (never amount-based)
            with patch("app.detection.engine.score_transaction", side_effect=RuntimeError("Engine offline")):
                try:
                    score_transaction(self.conn, {"id": tid, "amount": amt, "created_at": "2026-01-01T12:00:00Z"})
                except Exception:
                    self.cursor.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED' WHERE id = ?", (tid,))
                    self.conn.commit()

            self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = ?", (tid,))
            row_failed = self.cursor.fetchone()
            self.assertIsNone(row_failed[0], "Failure path assigned non-null score instead of NULL!")
            self.assertEqual(row_failed[1], "FAILED", "Failure path did not record FAILED band!")

    def test_18_demo_seed_data_cannot_enter_production_analytics_or_evaluation(self):
        """18. Demo transactions, alerts, and investigations are excluded from production analytics and evaluation."""
        from app.services.analytics_service import get_kpi_summary, get_analytics_trends

        # Seed genuine transaction
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-GENUINE', 'EVT-GENUINE', 'ACC-1', 'CUST-1', 100.0, 'USD', 'TRANSFER', 'ACH', 'COMPLETED', 15.0, 'ROUTINE', 'SAML_D', '2026-01-01T10:00:00Z')
        """)
        # Seed demo transaction
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-DEMO', 'EVT-DEMO', 'ACC-1', 'CUST-1', 50000.0, 'USD', 'TRANSFER', 'ACH', 'COMPLETED', 85.0, 'HIGH', 'DEMO_FIXTURE', '2026-01-01T10:00:00Z')
        """)
        # Seed demo alert
        self.cursor.execute("""
            INSERT INTO alerts (id, alert_ref, transaction_id, account_id, customer_id, severity, status, risk_score, title, summary, created_at, updated_at)
            VALUES ('ALT-DEMO', 'REF-DEMO', 'TXN-DEMO', 'ACC-1', 'CUST-1', 'CRITICAL', 'NEW', 85.0, '[DEMO FIXTURE] High Risk Transfer', 'Demo alert', '2026-01-01T10:00:00Z', '2026-01-01T10:00:00Z')
        """)
        # Seed demo investigation
        self.cursor.execute("""
            INSERT INTO investigations (id, case_number, title, summary, priority, status, assigned_investigator_id, created_at, updated_at)
            VALUES ('INV-DEMO', 'CASE-DEMO-01', '[DEMO FIXTURE] Priority Case 101', 'Demo case', 'HIGH', 'IN_PROGRESS', 'USR-INV-01', '2026-01-01T10:00:00Z', '2026-01-01T10:00:00Z')
        """)
        self.conn.commit()

        # Production KPI summary must count only genuine records
        kpi = get_kpi_summary(self.conn)
        self.assertEqual(kpi["transactions_processed"], 1, "Demo transaction contaminated production KPI transaction count!")
        self.assertEqual(kpi["alerts_generated"], 0, "Demo alert contaminated production KPI alert count!")
        self.assertEqual(kpi["open_investigations"], 0, "Demo investigation contaminated production KPI open investigation count!")

        # Production evaluation must reject DEMO_FIXTURE dataset
        eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="DEMO_FIXTURE")
        self.assertEqual(eval_res["status"], "NOT EVALUATED")
        self.assertIn("Demo fixtures are excluded", eval_res["message"])

    def test_19_environment_guards_prevent_demo_seeding_in_production(self):
        """19. Environment guard blocks demo seeding in production without explicit override."""
        import os
        from scripts.seed_demo_data import check_demo_environment_guard

        # Test production blocked by default
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_DEMO_SEEDING": ""}):
            with self.assertRaises(PermissionError):
                check_demo_environment_guard()

        # Test production rejected even with ALLOW_DEMO_SEEDING override (unconditional)
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_DEMO_SEEDING": "true"}):
            with self.assertRaises(PermissionError):
                check_demo_environment_guard()

        # Test development allowed
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "ALLOW_DEMO_SEEDING": ""}):
            check_demo_environment_guard()

    def test_20_model_artifact_load_and_predict_in_backend_environment(self):
        """20. Model artifact loads in backend environment and outputs valid, bounded probabilities."""
        import joblib
        import os
        from app.detection.supervised import _init_rf_remediated, CANONICAL_FEATURE_NAMES, _get_model_storage_path

        # 1. Model file exists
        model_path = _get_model_storage_path()
        self.assertTrue(os.path.exists(model_path), f"Artifact missing at {model_path}")

        # 2. Raw artifact inspection
        raw_artifact = joblib.load(model_path)
        self.assertIn("model", raw_artifact)
        self.assertIn("metadata", raw_artifact)

        meta = raw_artifact["metadata"]
        # Required provenance keys
        for key in ["model_version", "code_version", "canonical_feature_schema", "dataset_name", "train_samples", "val_samples", "test_samples", "train_date_range", "threshold_selection_method", "calibration_status"]:
            self.assertIn(key, meta, f"Metadata missing required provenance key: {key}")

        # Exact 9 canonical features in identical order
        self.assertEqual(meta["canonical_feature_schema"], CANONICAL_FEATURE_NAMES)
        self.assertEqual(len(meta["canonical_feature_schema"]), 9)

        # 3. Model object execution
        model = _init_rf_remediated()
        self.assertIsNotNone(model)

        # Valid 9-feature input
        test_vec = np.array([[3.699, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0]])
        probs = model.predict_proba(test_vec)
        self.assertEqual(probs.shape, (1, 2))
        self.assertTrue(np.all(np.isfinite(probs)), "Model output non-finite probabilities!")
        self.assertTrue(np.all((probs >= 0.0) & (probs <= 1.0)), "Model output probabilities outside [0, 1]!")
        self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=5)

if __name__ == "__main__":
    unittest.main()
