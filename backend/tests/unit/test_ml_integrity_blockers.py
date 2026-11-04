"""
SentinelFlow AI - AML Model Integrity & Remediation Blockers Test Suite.

Rigorously verifies:
1. SAML-D / NFPC seeding crash fix & graceful handling of zero scored transactions.
2. Separation of real dataset ingestion from demo fixtures.
3. Strict production environment guards for all demo/simulation operations.
4. Evaluator metric integrity: rejection of fabricated AUCs, handling of single-class, NaN, Inf, missing, unmatched.
5. Untouched-test partition verification with deliberate mixing of train/val/test records.
6. Persisted model artifact verification across 10 distinct failure and validation modes.
"""

import unittest
import sqlite3
import sys
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
_BACKEND_DIR = os.path.join(_BASE_DIR, "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
import tempfile
import joblib
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.core.database import SCHEMA_SQL
from app.core.guards import check_demo_environment_guard
from app.detection.features import CANONICAL_FEATURE_NAMES
from app.detection.supervised import (
    validate_model_artifact,
    RobustRandomForestClassifier,
    _init_rf_remediated,
    _get_model_storage_path,
    predict_supervised_risk,
    VERSION_V2_REMEDIATED
)
from app.evaluation.evaluator import IndependentEvaluator, _compute_auc_roc_and_pr
from scripts.seed_saml_and_nfpc import (
    seed_demo_fixtures_from_scored_txns,
    ingest_real_saml_and_nfpc_datasets,
    seed_saml_and_nfpc_database
)


class TestMLIntegrityBlockers(unittest.TestCase):

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
        self.cursor = self.conn.cursor()
        self.cursor.executescript(SCHEMA_SQL)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.environ.clear()
        os.environ.update(self._orig_env)

    # =========================================================================
    # SECTION 2: SAML-D / NFPC Seeding Crash Fixes
    # =========================================================================

    def test_01_seeding_zero_scored_transactions_no_crash(self):
        """1. When zero transactions have risk_score >= 65.0, demo fixture generation skips cleanly without ZeroDivisionError."""
        # Insert routine/unscored transactions (< 65.0 or NULL)
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-1', 'EVT-1', 'ACC-1', 'CUST-1', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', NULL, 'PENDING', 'SAML_D', '2026-01-01T10:00:00Z')
        """)
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-2', 'EVT-2', 'ACC-2', 'CUST-2', 50.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 15.0, 'ROUTINE', 'SAML_D', '2026-01-01T10:00:00Z')
        """)
        self.conn.commit()

        # Execute demo fixture generator directly on connection
        res = seed_demo_fixtures_from_scored_txns(conn=self.conn)
        self.assertEqual(res["status"], "SKIPPED_NO_SCORED_TRANSACTIONS")
        self.assertEqual(res["created_alerts"], 0)
        self.assertEqual(res["created_investigations"], 0)

        # Confirm no alerts or investigations were created
        self.cursor.execute("SELECT COUNT(*) FROM alerts")
        self.assertEqual(self.cursor.fetchone()[0], 0)
        self.cursor.execute("SELECT COUNT(*) FROM investigations")
        self.assertEqual(self.cursor.fetchone()[0], 0)

    def test_02_seeding_one_eligible_scored_transaction(self):
        """2. When exactly one eligible transaction exists, alert and investigations are created cleanly."""
        self.cursor.execute("""
            INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
            VALUES ('TXN-HIGH-1', 'EVT-H1', 'ACC-H1', 'CUST-H1', 75000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 88.5, 'HIGH', 'SAML_D', '2026-01-01T10:00:00Z')
        """)
        self.conn.commit()

        res = seed_demo_fixtures_from_scored_txns(conn=self.conn)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["created_alerts"], 1)
        self.assertGreater(res["created_investigations"], 0)

        self.cursor.execute("SELECT COUNT(*) FROM alerts")
        self.assertEqual(self.cursor.fetchone()[0], 1)

    def test_03_seeding_multiple_eligible_scored_transactions(self):
        """3. When multiple eligible transactions exist, alerts and investigations wrap correctly."""
        for i in range(5):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES (?, ?, ?, ?, 80000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', ?, 'HIGH', 'SAML_D', '2026-01-01T10:00:00Z')
            """, (f"TXN-MULTI-{i}", f"EVT-M-{i}", f"ACC-M-{i}", f"CUST-M-{i}", 70.0 + i * 4.0))
        self.conn.commit()

        res = seed_demo_fixtures_from_scored_txns(conn=self.conn)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["created_alerts"], 5)
        self.assertEqual(res["created_investigations"], 6)

    def test_04_scoring_engine_unavailable_preserves_null_and_failed_status(self):
        """4. When scoring engine returns None for risk score, risk_score remains NULL and risk_band is FAILED."""
        with patch("scripts.seed_saml_and_nfpc.score_transaction", return_value={"final_risk_score": None}):
            fake_batch = [{
                "id": "TXN-NFPC-FAIL-1",
                "event_id": "EVT-NFPC-F1",
                "source_account_id": "ACC-SRC-1",
                "destination_account_id": "ACC-DST-1",
                "amount": 250000.0,
                "currency": "INR",
                "created_at": "2026-01-01T10:00:00Z"
            }]
            with patch("app.data_ingestion.nfpc_adapter.NfpcAdapter.load_batches", return_value=[fake_batch]):
                with patch("app.data_ingestion.nfpc_adapter.NfpcAdapter.process_and_isolate", return_value=(fake_batch, MagicMock(labels_isolated=0))):
                    with patch("os.path.exists", side_effect=lambda p: "nfpc" in p):
                        ingest_real_saml_and_nfpc_datasets(conn=self.conn, purge_existing=False)

        self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = 'TXN-NFPC-FAIL-1'")
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row[0], "Unavailable score was not preserved as NULL!")
        self.assertEqual(row[1], "FAILED", "Unavailable score was not given FAILED risk_band!")

    def test_05_scoring_engine_exception_preserves_null_and_failed_status(self):
        """5. When scoring engine raises an exception, risk_score remains NULL and risk_band is FAILED."""
        with patch("scripts.seed_saml_and_nfpc.score_transaction", side_effect=RuntimeError("Scoring engine crashed")):
            fake_batch = [{
                "id": "TXN-NFPC-EX-1",
                "event_id": "EVT-NFPC-EX1",
                "source_account_id": "ACC-SRC-EX",
                "destination_account_id": "ACC-DST-EX",
                "amount": 100000.0,
                "currency": "INR",
                "created_at": "2026-01-01T10:00:00Z"
            }]
            with patch("app.data_ingestion.nfpc_adapter.NfpcAdapter.load_batches", return_value=[fake_batch]):
                with patch("app.data_ingestion.nfpc_adapter.NfpcAdapter.process_and_isolate", return_value=(fake_batch, MagicMock(labels_isolated=0))):
                    with patch("os.path.exists", side_effect=lambda p: "nfpc" in p):
                        ingest_real_saml_and_nfpc_datasets(conn=self.conn, purge_existing=False)

        self.cursor.execute("SELECT risk_score, risk_band FROM transactions WHERE id = 'TXN-NFPC-EX-1'")
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row[0], "Exception path assigned non-null score instead of NULL!")
        self.assertEqual(row[1], "FAILED", "Exception path did not record FAILED risk_band!")

    # =========================================================================
    # SECTION 3: Demo Fixture vs Real Ingestion Separation
    # =========================================================================

    def test_06_production_mode_rejects_demo_seeding(self):
        """6. Production mode strictly rejects demo seeding entry points unconditionally."""
        env_vars = ["ENVIRONMENT", "APP_ENV", "NODE_ENV", "ENV", "SENTINELFLOW_ENV", "STAGE", "TARGET_ENV"]
        for env_var in env_vars:
            for val in ["production", "prod", "live"]:
                with patch.dict(os.environ, {env_var: val, "ALLOW_DEMO_SEEDING": ""}):
                    with self.assertRaises(PermissionError):
                        check_demo_environment_guard()

        # ALLOW_DEMO_SEEDING=true must NEVER override a production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_DEMO_SEEDING": "true"}):
            with self.assertRaises(PermissionError):
                check_demo_environment_guard()

    def test_07_real_ingestion_creates_no_demo_fixtures(self):
        """7. Real dataset ingestion creates 0 demo alerts, 0 investigations, and 0 demo feedback."""
        fake_saml = [{
            "id": "TXN-SAML-REAL-01",
            "event_id": "EVT-SAML-R1",
            "source_account_id": "ACC-S1",
            "destination_account_id": "ACC-D1",
            "amount": 5000.0,
            "currency": "USD",
            "created_at": "2022-10-07T22:00:00Z"
        }]
        with patch("app.data_ingestion.saml_d_adapter.SamlDAdapter.load_batches", return_value=[fake_saml]):
            with patch("app.data_ingestion.saml_d_adapter.SamlDAdapter.process_and_isolate", return_value=(fake_saml, MagicMock(labels_isolated=1))):
                with patch("os.path.exists", side_effect=lambda p: "saml_d" in p):
                    with patch("scripts.seed_saml_and_nfpc.score_transaction", return_value={"final_risk_score": 75.0, "risk_band": "HIGH"}):
                        ingest_real_saml_and_nfpc_datasets(conn=self.conn, purge_existing=False)

        # Confirm zero demo alerts, zero investigations, zero analyst feedback
        self.cursor.execute("SELECT COUNT(*) FROM alerts")
        self.assertEqual(self.cursor.fetchone()[0], 0, "Real ingestion created alerts!")

        self.cursor.execute("SELECT COUNT(*) FROM investigations")
        self.assertEqual(self.cursor.fetchone()[0], 0, "Real ingestion created investigations!")

        self.cursor.execute("SELECT COUNT(*) FROM analyst_feedback")
        self.assertEqual(self.cursor.fetchone()[0], 0, "Real ingestion created analyst feedback!")

    def test_08_demo_feedback_cannot_become_eligible_training_feedback(self):
        """8. Demo feedback is tagged is_eligible_for_training=0 and exclusion_reason='DEMO_FIXTURE'."""
        self.cursor.execute("""
            INSERT INTO investigations (id, case_number, title, summary, priority, status, assigned_investigator_id, created_at, updated_at)
            VALUES ('INV-DEMO-1', 'CASE-DEMO-1', '[DEMO FIXTURE] Priority Case', 'Summary', 'HIGH', 'RESOLVED', 'USR-1', '2026-01-01T10:00:00Z', '2026-01-01T10:00:00Z')
        """)
        self.cursor.execute("""
            INSERT INTO analyst_feedback (
                id, investigation_id, analyst_id, disposition, rationale,
                evidence_reviewed_count, is_eligible_for_training, training_label,
                exclusion_reason, model_version, rule_version, created_at
            ) VALUES ('FB-DEMO-1', 'INV-DEMO-1', 'USR-1', 'CONFIRMED_FRAUD', 'Demo note', 4, 0, NULL, 'DEMO_FIXTURE', 'v1', 'v1', '2026-01-01T10:00:00Z')
        """)
        self.conn.commit()

        from app.learning.dataset_builder import build_training_dataset
        dataset = build_training_dataset(self.conn)
        self.assertEqual(len(dataset["samples"]), 0, "Demo feedback leaked into eligible training dataset samples!")

    # =========================================================================
    # SECTION 4: Fix Misleading Evaluator Metrics
    # =========================================================================

    def test_09_evaluator_auc_computation_exception_returns_none(self):
        """9. When AUC calculation raises an exception, metrics report roc_auc: None, pr_auc: None (never 0.50 or prevalence)."""
        prot_labels = {
            "TXN-AUC-0": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"},
            "TXN-AUC-1": {"is_laundering": 1, "laundering_type": "FanOut", "created_at": "2022-10-01T10:00:00Z"}
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-AUC-0', 'EVT-0', 'A', 'C', 10.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 10.0, 'ROUTINE', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-AUC-1', 'EVT-1', 'A', 'C', 1000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 90.0, 'HIGH', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.conn.commit()

            with patch("app.evaluation.evaluator._compute_auc_roc_and_pr", side_effect=RuntimeError("AUC calculation failed")):
                eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
                self.assertEqual(eval_res["status"], "EVALUATED")
                metrics = eval_res["metrics"]
                self.assertIsNone(metrics["roc_auc"], "Fabricated 0.50 ROC-AUC returned upon exception!")
                self.assertIsNone(metrics["pr_auc"], "Fabricated prevalence PR-AUC returned upon exception!")
                self.assertIn("CALCULATION_UNAVAILABLE", metrics["auc_status"])

    def test_10_evaluator_no_positive_examples_reports_unavailable(self):
        """10. Single-class evaluation with zero positives reports auc_status UNAVAILABLE_NO_POSITIVE_EXAMPLES and None AUCs."""
        prot_labels = {
            f"TXN-NEG-{i}": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"}
            for i in range(5)
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            for i in range(5):
                tid = f"TXN-NEG-{i}"
                self.cursor.execute("""
                    INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                    VALUES (?, ?, 'A', 'C', 10.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 10.0, 'ROUTINE', 'SAML_D', '2022-10-01T10:00:00Z')
                """, (tid, f"EVT-{tid}"))
            self.conn.commit()

            eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
            self.assertEqual(eval_res["status"], "EVALUATED")
            metrics = eval_res["metrics"]
            self.assertIsNone(metrics["roc_auc"], "Fabricated ROC-AUC substituted for single-class set!")
            self.assertIsNone(metrics["pr_auc"], "Fabricated PR-AUC substituted for single-class set!")
            self.assertEqual(metrics["auc_status"], "UNAVAILABLE_NO_POSITIVE_EXAMPLES")

    def test_11_evaluator_no_negative_examples_reports_unavailable(self):
        """11. Single-class evaluation with zero negatives reports auc_status UNAVAILABLE_NO_NEGATIVE_EXAMPLES and None AUCs."""
        prot_labels = {
            f"TXN-POS-{i}": {"is_laundering": 1, "laundering_type": "FanOut", "created_at": "2022-10-01T10:00:00Z"}
            for i in range(5)
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            for i in range(5):
                tid = f"TXN-POS-{i}"
                self.cursor.execute("""
                    INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                    VALUES (?, ?, 'A', 'C', 1000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 90.0, 'HIGH', 'SAML_D', '2022-10-01T10:00:00Z')
                """, (tid, f"EVT-{tid}"))
            self.conn.commit()

            eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
            self.assertEqual(eval_res["status"], "EVALUATED")
            metrics = eval_res["metrics"]
            self.assertIsNone(metrics["roc_auc"])
            self.assertIsNone(metrics["pr_auc"])
            self.assertEqual(metrics["auc_status"], "UNAVAILABLE_NO_NEGATIVE_EXAMPLES")

    def test_12_evaluator_rejects_nan_prediction(self):
        """12. Evaluator strictly rejects NaN prediction scores with status NOT EVALUATED."""
        prot_labels = {"TXN-NAN-1": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"}}
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-NAN-1', 'EVT-NAN', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 'NaN', 'ROUTINE', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.conn.commit()

            eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
            self.assertEqual(eval_res["status"], "NOT EVALUATED")
            self.assertIn("non-finite", eval_res["message"].lower())
            self.assertEqual(eval_res["sample_accounting"]["invalid_predictions"], 1)

    def test_13_evaluator_rejects_infinite_prediction(self):
        """13. Evaluator strictly rejects Infinity prediction scores with status NOT EVALUATED."""
        prot_labels = {"TXN-INF-1": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"}}
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-INF-1', 'EVT-INF', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 'Infinity', 'HIGH', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.conn.commit()

            eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
            self.assertEqual(eval_res["status"], "NOT EVALUATED")
            self.assertIn("non-finite", eval_res["message"].lower())

    def test_14_evaluator_missing_and_unmatched_predictions_reconciliation(self):
        """14. Missing and unmatched predictions are segregated cleanly from matched evaluations."""
        prot_labels = {
            "TXN-MATCH": {"is_laundering": 1, "laundering_type": "Layering", "created_at": "2022-10-01T10:00:00Z"},
            "TXN-MISSING": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"}
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-MATCH', 'EVT-1', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 80.0, 'HIGH', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-MISSING', 'EVT-2', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', NULL, 'PENDING', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-UNMATCHED', 'EVT-3', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 50.0, 'ROUTINE', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.conn.commit()

            eval_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D")
            acct = eval_res["sample_accounting"]
            self.assertEqual(acct["matched_predictions"], 1)
            self.assertEqual(acct["missing_predictions"], 1)
            self.assertEqual(acct["unmatched_predictions"], 1)

    def test_15_evaluator_scope_distinction(self):
        """15. Full dataset benchmark is clearly distinguished from untouched test set."""
        prot_labels = {"TXN-SAML-0001": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-01T10:00:00Z"}}
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-0001', 'EVT-1', 'A', 'C', 100.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 10.0, 'ROUTINE', 'SAML_D', '2022-10-01T10:00:00Z')
            """)
            self.conn.commit()

            full_res = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D", eval_split="ALL")
            self.assertFalse(full_res["is_untouched_test"])
            self.assertEqual(full_res["evaluation_type"], "FULL_DATASET_BENCHMARK")
            self.assertIn("NOT independent holdout test performance", full_res["scope_note"])

    # =========================================================================
    # SECTION 5: Strengthen Untouched-Test Partition Verification
    # =========================================================================

    def test_16_deliberate_partition_mixing_blocks_train_and_val_from_test_metrics(self):
        """16. When train, val, and test records are mixed, ONLY verified test records enter test metrics."""
        prot_labels = {
            # Train partition (Index 100, timestamp in train range)
            "TXN-SAML-000100": {"is_laundering": 1, "laundering_type": "FanIn", "created_at": "2022-09-02T10:00:00Z"},
            # Validation partition (Index 15000, timestamp in val range)
            "TXN-SAML-015000": {"is_laundering": 0, "laundering_type": "Normal", "created_at": "2022-10-07T20:00:00Z"},
            # Verified Test record (Index 20000, timestamp in test range)
            "TXN-SAML-020000": {"is_laundering": 1, "laundering_type": "Layering", "created_at": "2022-10-07T23:00:00Z"},
            # Conflicting record (Index 21000 claims test, but timestamp is in train range)
            "TXN-SAML-021000": {"is_laundering": 1, "laundering_type": "Layering", "created_at": "2022-09-01T12:00:00Z"}
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-000100', 'EVT-TR', 'A', 'C', 5000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 90.0, 'HIGH', 'SAML_D', '2022-09-02T10:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-015000', 'EVT-VAL', 'A', 'C', 500.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 15.0, 'ROUTINE', 'SAML_D', '2022-10-07T20:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-020000', 'EVT-TST', 'A', 'C', 10000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 85.0, 'HIGH', 'SAML_D', '2022-10-07T23:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-021000', 'EVT-CONFLICT', 'A', 'C', 10000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 85.0, 'HIGH', 'SAML_D', '2022-09-01T12:00:00Z')
            """)
            self.conn.commit()

            # Evaluate strictly on TEST split
            test_eval = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D", eval_split="TEST")
            self.assertEqual(test_eval["status"], "EVALUATED")
            self.assertTrue(test_eval["is_untouched_test"])

            # Exactly 1 record (TXN-SAML-020000) qualifies for untouched test
            self.assertEqual(test_eval["total_evaluated_samples"], 1)
            self.assertEqual(test_eval["confusion_matrix"]["reconciled_total"], 1)

            # Confirm partition accounting tracks train, val, and conflicting records
            pa = test_eval["partition_accounting"]
            self.assertEqual(pa["train_partition"]["verified_sample_count"], 1)
            self.assertEqual(pa["validation_partition"]["verified_sample_count"], 1)
            self.assertEqual(pa["test_partition"]["verified_sample_count"], 1)
            self.assertEqual(pa["unverified_partition_records"], 1)

    # =========================================================================
    # SECTION 6: Model Artifact Verification Across Failure Modes
    # =========================================================================

    def test_17_valid_model_artifact_passes_validation(self):
        """17. Valid model artifact dictionary passes validation."""
        rf = RobustRandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
        X = np.random.randn(50, 9)
        y = np.random.choice([0, 1], size=50)
        rf.fit(X, y)

        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        artifact = {"model": rf, "metadata": meta}
        is_valid, reason = validate_model_artifact(artifact)
        self.assertTrue(is_valid, f"Valid artifact failed validation: {reason}")
        self.assertIsNone(reason)

    def test_18_artifact_missing_metadata_rejected(self):
        """18. Artifact missing metadata dictionary is rejected."""
        rf = RobustRandomForestClassifier()
        artifact = {"model": rf}
        is_valid, reason = validate_model_artifact(artifact)
        self.assertFalse(is_valid)
        self.assertIn("metadata", reason.lower())

    def test_19_artifact_wrong_feature_schema_rejected(self):
        """19. Artifact with wrong feature schema names or count is rejected."""
        rf = RobustRandomForestClassifier()
        bad_meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": ["feat_1", "feat_2"],
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": rf, "metadata": bad_meta})
        self.assertFalse(is_valid)
        self.assertIn("incompatible feature schema", reason.lower())

    def test_20_artifact_wrong_feature_count_rejected(self):
        """20. Model object with wrong n_features_in_ is rejected."""
        rf = RobustRandomForestClassifier()
        rf.n_features_in_ = 8  # Mismatched from 9
        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": rf, "metadata": meta})
        self.assertFalse(is_valid)
        self.assertIn("n_features_in_", reason)

    def test_21_artifact_wrong_estimator_type_rejected(self):
        """21. Artifact with unsupported estimator type is rejected."""
        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": "random_forest_string", "metadata": meta})
        self.assertFalse(is_valid)
        self.assertIn("predict_proba", reason.lower())

    def test_22_artifact_missing_prediction_interface_rejected(self):
        """22. Estimator lacking predict_proba method is rejected."""
        class DummyEstimator:
            def predict(self, X):
                return np.zeros(len(X))

        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": DummyEstimator(), "metadata": meta})
        self.assertFalse(is_valid)
        self.assertIn("predict_proba", reason.lower())

    def test_23_artifact_incorrect_classes_rejected(self):
        """23. Estimator with non-binary classes is rejected."""
        rf = RobustRandomForestClassifier()
        rf.n_features_in_ = 9
        rf.feature_names_in_ = CANONICAL_FEATURE_NAMES
        rf.classes_ = np.array([0, 1, 2])  # Multi-class
        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": rf, "metadata": meta})
        self.assertFalse(is_valid)
        self.assertIn("classes_", reason)

    def test_24_artifact_nan_prediction_probabilities_rejected(self):
        """24. Estimator returning NaN probabilities is rejected."""
        class NanPredictor(RobustRandomForestClassifier):
            n_features_in_ = 9
            feature_names_in_ = CANONICAL_FEATURE_NAMES
            classes_ = np.array([0, 1])
            is_fitted = True
            def predict_proba(self, X):
                return np.array([[np.nan, np.nan]])

        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 50,
            "val_samples": 10,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": NanPredictor(), "metadata": meta})
        self.assertFalse(is_valid)
        self.assertIn("non-finite", reason.lower())

    def test_25_corrupt_artifact_file_fails_closed(self):
        """25. Corrupted artifact file on disk fails closed by returning None rather than crashing or activating synthetic data."""
        import app.detection.supervised as sup_module
        sup_module._rf_remediated_model = None

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            f.write(b"CORRUPTED_BINARY_DATA_NOT_A_VALID_PICKLE")
            temp_path = f.name

        try:
            with patch("app.detection.supervised._get_model_storage_path", return_value=temp_path):
                with patch("os.path.exists", side_effect=lambda p: p == temp_path):
                    model = _init_rf_remediated()
                    self.assertIsNone(model, "Corrupted artifact did not fail closed to None!")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_26_missing_canonical_training_data_returns_model_unavailable(self):
        """26. When no artifact exists and canonical dataset is missing, loader returns None without activating synthetic data."""
        import app.detection.supervised as sup_module
        sup_module._rf_remediated_model = None

        with patch("app.detection.supervised._get_model_storage_path", return_value="/nonexistent/model.joblib"):
            with patch("os.path.exists", return_value=False):
                model = _init_rf_remediated()
                self.assertIsNone(model, "Missing canonical data activated fallback instead of returning None!")

                # Confirm predict_supervised_risk returns MODEL_UNAVAILABLE
                res = predict_supervised_risk({
                    "amount": 100.0,
                    "velocity_10m": 1.0,
                    "rapid_movement": 0.0,
                    "structuring_flag": 0.0,
                    "is_cross_border": 0.0,
                    "is_cash_channel": 0.0,
                    "is_new_recipient": 0.0,
                    "past_recipient_count": 0.0,
                    "history_length": 1.0
                })
                self.assertEqual(res["model_status"], "MODEL_UNAVAILABLE")
                self.assertIsNone(res["supervised_score"])



    # =========================================================================
    # SECTION 7: Verifiable Partition Provenance, Internal Guards & Upsert Status
    # =========================================================================

    def test_27_evaluator_rejects_record_with_test_timestamp_lacking_canonical_identity(self):
        """27. Timestamp alone NEVER qualifies a record as an untouched test record. Unverifiable IDs are rejected."""
        prot_labels = {
            "TXN-CUSTOM-UNKNOWN": {"is_laundering": 1, "laundering_type": "TEST", "created_at": "2022-10-07T23:00:00Z"},
            "TXN-SAML-020000": {"is_laundering": 1, "laundering_type": "TEST", "created_at": "2022-10-07T23:00:00Z"}
        }
        with patch("app.evaluation.evaluator.get_protected_evaluation_labels", return_value={"transactions": prot_labels}):
            # Insert both with test timestamps (>= 2022-10-07T21:44:14Z)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-CUSTOM-UNKNOWN', 'EVT-UNK', 'A', 'C', 5000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 85.0, 'HIGH', 'SAML_D', '2022-10-07T23:00:00Z')
            """)
            self.cursor.execute("""
                INSERT INTO transactions (id, event_id, source_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at)
                VALUES ('TXN-SAML-020000', 'EVT-VALID', 'A', 'C', 5000.0, 'USD', 'TRANSFER', 'WIRE', 'COMPLETED', 85.0, 'HIGH', 'SAML_D', '2022-10-07T23:00:00Z')
            """)
            self.conn.commit()

            test_eval = IndependentEvaluator.evaluate_transaction_level(self.conn, dataset_name="SAML_D", eval_split="TEST")
            self.assertEqual(test_eval["status"], "EVALUATED")
            # Only TXN-SAML-020000 was evaluated; TXN-CUSTOM-UNKNOWN was rejected as unverified
            self.assertEqual(test_eval["total_evaluated_samples"], 1)
            pa = test_eval["partition_accounting"]
            self.assertEqual(pa["test_partition"]["verified_sample_count"], 1)
            self.assertEqual(pa["unverified_partition_records"], 1)

    def test_28_evaluator_discloses_actual_split_proportions_56_14_30(self):
        """28. Evaluation partition accounting explicitly discloses canonical 56% / 14% / 30% split proportions."""
        res_saml = IndependentEvaluator.evaluate_saml_untouched_test_set(risk_threshold=55.0)
        pa = res_saml["partition_accounting"]
        self.assertIn("manifest_provenance", pa)
        prov = pa["manifest_provenance"]
        self.assertEqual(prov["split_proportions"]["train"], 0.56)
        self.assertEqual(prov["split_proportions"]["validation"], 0.14)
        self.assertEqual(prov["split_proportions"]["test"], 0.30)
        self.assertIn("56.0% Train", prov["disclosure"])
        self.assertIn("30.0% Untouched Test", prov["disclosure"])
        self.assertNotIn("70% / 15% / 15%", str(pa))

    def test_29_guard_rejects_demo_seeding_targeting_production_database(self):
        """29. Demo environment guard unconditionally rejects execution targeting a production database."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://app:secret@db-prod.internal.sentinelflow.io:5432/main", "ALLOW_DEMO_SEEDING": "true"}):
            with self.assertRaises(PermissionError) as ctx:
                check_demo_environment_guard("Demo seeding")
            self.assertIn("TARGET DATABASE IS PRODUCTION", str(ctx.exception))

    def test_30_bulk_ingest_supabase_demo_function_has_internal_guard(self):
        """30. seed_demo_investigations_and_feedback in bulk_ingest_supabase has an internal production guard."""
        from scripts.bulk_ingest_supabase import seed_demo_investigations_and_feedback
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_DEMO_SEEDING": ""}):
            with self.assertRaises(PermissionError):
                seed_demo_investigations_and_feedback(cur=MagicMock(), conn=MagicMock())

    def test_31_upsert_records_stale_scoring_status_on_scoring_failure(self):
        """31. Upsert behavior records scoring_status = 'STALE' when re-scoring fails on existing scored record."""
        from app.api.v1.datasets import _persist_canonical_records
        
        # 1. Ingest initial transaction with genuine score
        initial_batch = [{
            "id": "TXN-STALE-CHECK-1",
            "event_id": "EVT-STALE-1",
            "source_account_id": "ACC-STALE-SRC",
            "destination_account_id": "ACC-STALE-DST",
            "customer_id": "CUST-STALE",
            "amount": 1000.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ACH",
            "created_at": "2026-01-01T12:00:00Z"
        }]
        with patch("app.detection.engine.score_transaction", return_value={"final_risk_score": 42.0, "risk_band": "LOW", "triggered_rules": []}):
            res1 = _persist_canonical_records(self.conn, initial_batch, "AUDIT_DS")
        self.assertEqual(res1["scored_count"], 1)

        self.cursor.execute("SELECT risk_score, risk_band, scoring_status FROM transactions WHERE id = 'TXN-STALE-CHECK-1'")
        row1 = self.cursor.fetchone()
        self.assertEqual(row1[0], 42.0)
        self.assertEqual(row1[2], "CURRENT")

        # 2. Re-ingest with simulated scoring engine failure
        with patch("app.detection.engine.score_transaction", side_effect=RuntimeError("Engine offline")):
            res2 = _persist_canonical_records(self.conn, initial_batch, "AUDIT_DS")

        # Scoring failure must be visible in ingestion results
        self.assertEqual(res2["failed_count"], 1)
        self.assertEqual(len(res2["scoring_failures"]), 1)
        self.assertEqual(res2["scoring_failures"][0]["transaction_id"], "TXN-STALE-CHECK-1")

        # Upsert must preserve previous score without hiding that it is now STALE
        self.cursor.execute("SELECT risk_score, risk_band, scoring_status FROM transactions WHERE id = 'TXN-STALE-CHECK-1'")
        row2 = self.cursor.fetchone()
        self.assertEqual(row2[0], 42.0, "Score was corrupted on failure!")
        self.assertEqual(row2[2], "STALE", "Scoring failure was silently preserved as CURRENT instead of marked STALE!")

    def test_32_model_artifact_validation_requires_n_features_and_classes(self):
        """32. Model artifact validation strictly requires n_features_in_ and classes_ attributes."""
        rf = RobustRandomForestClassifier(n_estimators=5, max_depth=3, random_state=42)
        X = np.random.randn(20, 9)
        y = np.random.choice([0, 1], size=20)
        rf.fit(X, y)

        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 20,
            "val_samples": 5,
            "train_date_range": ("2022-09-01", "2022-10-07"),
            "threshold_selection_method": "validation_grid_search"
        }

        # Subclass missing n_features_in_
        class MissingNFeatures(RobustRandomForestClassifier):
            @property
            def n_features_in_(self):
                return None
        
        m_bad_features = MissingNFeatures(n_estimators=5)
        m_bad_features.fit(X, y)
        is_val, r = validate_model_artifact({"model": m_bad_features, "metadata": meta})
        self.assertFalse(is_val)
        self.assertIn("n_features_in_", r)

        # Subclass missing classes_
        class MissingClasses(RobustRandomForestClassifier):
            @property
            def classes_(self):
                return None

        m_bad_classes = MissingClasses(n_estimators=5)
        m_bad_classes.fit(X, y)
        is_val2, r2 = validate_model_artifact({"model": m_bad_classes, "metadata": meta})
        self.assertFalse(is_val2)
        self.assertIn("classes_", r2)

    def test_33_unfitted_classifier_has_no_defaults_and_fails_validation(self):
        """33. Unfitted RobustRandomForestClassifier has is_fitted=False, no default feature attributes, and fails validation."""
        unfitted = RobustRandomForestClassifier()
        self.assertFalse(unfitted.is_fitted, "Unfitted classifier reported is_fitted=True!")
        self.assertIsNone(unfitted.n_features_in_, "Unfitted classifier returned non-None n_features_in_!")
        self.assertIsNone(unfitted.feature_names_in_, "Unfitted classifier returned non-None feature_names_in_!")
        self.assertIsNone(unfitted.classes_, "Unfitted classifier returned non-None classes_!")

        meta = {
            "model_version": VERSION_V2_REMEDIATED,
            "dataset_name": "SAML_D",
            "canonical_feature_schema": CANONICAL_FEATURE_NAMES,
            "train_samples": 14000,
            "val_samples": 3500,
            "train_date_range": ("2022-10-07 10:35:19", "2022-10-07 19:26:11"),
            "threshold_selection_method": "validation_grid_search"
        }
        is_valid, reason = validate_model_artifact({"model": unfitted, "metadata": meta})
        self.assertFalse(is_valid, "Unfitted classifier passed artifact validation!")
        self.assertIn("n_features_in_", reason.lower(), f"Unexpected failure reason: {reason}")

    def test_34_committed_artifact_validation_and_runtime_bounded_prediction(self):
        """34. Committed artifact supervised_rf_v2.joblib passes validation, has 60 trees, exact canonical feature order, and bounded predictions."""
        import joblib
        from app.detection.supervised import _get_model_storage_path

        artifact_path = _get_model_storage_path()
        self.assertTrue(os.path.exists(artifact_path), f"Artifact missing at {artifact_path}")

        artifact = joblib.load(artifact_path)
        is_valid, reason = validate_model_artifact(artifact)
        self.assertTrue(is_valid, f"Committed artifact failed validation: {reason}")

        model = artifact["model"]
        self.assertTrue(hasattr(model, "is_fitted") and model.is_fitted, "Committed model is not fitted!")
        self.assertEqual(len(model.trees), 60, "Committed model does not have 60 estimators!")
        self.assertEqual(list(model.feature_names_in_), CANONICAL_FEATURE_NAMES, "Committed model feature order mismatch!")
        self.assertEqual(model.n_features_in_, len(CANONICAL_FEATURE_NAMES))

        # Runtime prediction tests on edge inputs
        test_inputs = np.array([
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [10.0, 50.0, 1.0, 1.0, 1.0, 1.0, 1.0, 20.0, 100.0],
            [3.5, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 15.0]
        ], dtype=float)
        probs = model.predict_proba(test_inputs)
        self.assertEqual(probs.shape, (3, 2))
        self.assertTrue(np.all(np.isfinite(probs)), "Predictions contain NaN or Inf!")
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0), "Probabilities outside [0, 1]!")
        self.assertTrue(np.allclose(np.sum(probs, axis=1), 1.0), "Probabilities do not sum to 1.0!")

    def test_35_all_demo_entry_points_unconditionally_reject_production(self):
        """35. All demo entry points (seed, bulk demo, simulation, reset, scenario) reject production unconditionally."""
        from scripts.seed_demo_data import seed_demo_database
        from scripts.bulk_ingest_supabase import seed_demo_investigations_and_feedback
        from app.services.transaction_simulator import simulation_service
        from scripts.reset_demo_data import reset_demo_database

        for allow_override in ["", "true", "1"]:
            env_patch = {"ENVIRONMENT": "production", "ALLOW_DEMO_SEEDING": allow_override}
            with patch.dict(os.environ, env_patch):
                # 1. seed_demo_data
                with self.assertRaises(PermissionError):
                    seed_demo_database()

                # 2. bulk_ingest_supabase demo seeding
                with self.assertRaises(PermissionError):
                    seed_demo_investigations_and_feedback(cur=MagicMock())

                # 3. transaction_simulator streaming
                with self.assertRaises(PermissionError):
                    simulation_service.start_simulation()

                # 4. transaction_simulator scenario
                with self.assertRaises(PermissionError):
                    simulation_service.run_named_scenario("rapid_movement")

                # 5. reset_demo_data
                with self.assertRaises(PermissionError):
                    reset_demo_database()

    def test_36_database_safety_rejects_remote_targets_regardless_of_substrings(self):
        """36. Database safety check rejects remote and cloud hosts even when URL lacks 'prod' or 'live'."""
        remote_urls = [
            "postgresql://app:secret@db.supabase.co:5432/main",
            "postgresql://user:pass@mydb.rds.amazonaws.com:5432/db",
            "postgresql://user:pass@external-server.internal:5432/finance",
            "postgresql://user:pass@192.168.1.100:5432/analytics"
        ]
        for url in remote_urls:
            with patch.dict(os.environ, {"DATABASE_URL": url, "ENVIRONMENT": "development", "ALLOW_DEMO_SEEDING": "true"}):
                with self.assertRaises(PermissionError):
                    check_demo_environment_guard("Remote DB Safety Test")

if __name__ == "__main__":
    unittest.main()
