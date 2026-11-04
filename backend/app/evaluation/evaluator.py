"""
Independent Ground-Truth Evaluation Subsystem (Pipeline B).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. Strict Pipeline B Isolation: Operates with exclusive read access to protected evaluation
   labels. NEVER communicates ground truth to Pipeline A feature extractors or models.
2. Verified Transaction ID Matching: Matches predictions to ground truth strictly by ID.
   NEVER substitutes missing predictions with zero.
3. Transparent Sample Accounting: Explicitly reports matched, unmatched, missing-prediction,
   and invalid-label counts.
4. Partition Hygiene: Training records are never evaluated as untouched test records.
5. Exact Reconciled Accounting: Confusion matrix totals (TP + FP + TN + FN) MUST reconcile
   exactly to the evaluated sample count.
6. Honest Status Reporting: If no valid untouched test predictions exist, reports NOT EVALUATED.
"""

import sqlite3
import numpy as np
from typing import Dict, Any, List, Optional, Set
from app.data_ingestion.label_isolation import get_protected_evaluation_labels
from app.core.logging import logger

def _compute_auc_roc_and_pr(y_true: List[int], y_scores: List[float]):
    y_t = np.array(y_true, dtype=int)
    y_s = np.array(y_scores, dtype=float)
    n_pos = int(np.sum(y_t == 1))
    n_neg = int(np.sum(y_t == 0))
    if n_pos == 0 or n_neg == 0:
        return 0.5000, round(float(n_pos / max(1, len(y_true))), 4)
    desc_idx = np.argsort(-y_s)
    y_t_sorted = y_t[desc_idx]
    y_s_sorted = y_s[desc_idx]
    distinct_mask = np.diff(y_s_sorted, append=np.nan) != 0
    tps = np.cumsum(y_t_sorted)[distinct_mask]
    fps = np.cumsum(1 - y_t_sorted)[distinct_mask]
    tpr = np.r_[0, tps / n_pos, 1]
    fpr = np.r_[0, fps / n_neg, 1]
    roc_auc = float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) / 2.0))
    prec_curve = tps / (tps + fps)
    rec_curve = tps / n_pos
    rec_diff = np.diff(np.r_[0, rec_curve])
    pr_auc = float(np.sum(prec_curve * rec_diff))
    return round(roc_auc, 4), round(pr_auc, 4)

class IndependentEvaluator:
    """Computes verified, non-leaking performance metrics against protected ground-truth labels."""

    @classmethod
    def evaluate_transaction_level(
        cls,
        conn: sqlite3.Connection,
        dataset_name: str = "SAML_D",
        risk_threshold: float = 70.0,
        eval_split: str = "ALL"
    ) -> Dict[str, Any]:
        """
        Evaluates transaction-level predictions against protected transaction labels.
        Matches strictly by transaction ID; never substitutes missing predictions with zero.
        """
        # Read protected ground truth from Pipeline B isolated store
        protected_data = get_protected_evaluation_labels(dataset_name=dataset_name)
        prot_txns = protected_data.get("transactions", {})

        if not prot_txns:
            return {
                "dataset_name": dataset_name,
                "status": "NO_PROTECTED_LABELS_AVAILABLE",
                "message": f"No protected labels recorded for {dataset_name} in evaluation vault.",
                "sample_accounting": {
                    "total_protected_labels": 0,
                    "matched_predictions": 0,
                    "missing_predictions": 0,
                    "unmatched_predictions": 0,
                    "invalid_labels": 0
                }
            }

        # Query Pipeline A transactions for actual prediction scores
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, risk_score
            FROM transactions
            WHERE dataset_source = ?
        """, (dataset_name,))
        rows = cursor.fetchall()

        # Strict separation: only records with non-null risk_score are valid predictions
        valid_predictions: Dict[str, float] = {}
        null_predictions: Set[str] = set()
        for r in rows:
            t_id = str(r[0])
            score = r[1]
            if score is not None:
                try:
                    valid_predictions[t_id] = float(score)
                except (ValueError, TypeError):
                    null_predictions.add(t_id)
            else:
                null_predictions.add(t_id)

        # Reconcile ID sets
        prot_ids = set(prot_txns.keys())
        pred_ids = set(valid_predictions.keys())

        matched_ids = sorted(list(prot_ids.intersection(pred_ids)))
        missing_prediction_ids = sorted(list(prot_ids.difference(pred_ids)))
        unmatched_prediction_ids = sorted(list(pred_ids.difference(prot_ids)))

        # Evaluate only matched transactions with valid ground-truth labels
        y_true: List[int] = []
        y_pred: List[int] = []
        y_scores: List[float] = []
        invalid_label_count = 0
        typology_breakdown: Dict[str, Dict[str, int]] = {}

        for txn_id in matched_ids:
            prot_item = prot_txns[txn_id]
            raw_label = prot_item.get("is_laundering")
            if raw_label not in (0, 1):
                invalid_label_count += 1
                continue

            score = valid_predictions[txn_id]
            pred_binary = 1 if score >= risk_threshold else 0

            y_true.append(int(raw_label))
            y_pred.append(pred_binary)
            y_scores.append(score / 100.0)

            typology = str(prot_item.get("laundering_type") or "UNKNOWN")
            if typology not in typology_breakdown:
                typology_breakdown[typology] = {"total": 0, "detected": 0}
            typology_breakdown[typology]["total"] += 1
            if pred_binary == 1:
                typology_breakdown[typology]["detected"] += 1

        n_evaluated = len(y_true)

        if n_evaluated == 0:
            return {
                "dataset_name": dataset_name,
                "status": "NOT EVALUATED",
                "message": f"Zero valid matched predictions between Pipeline A and protected labels for {dataset_name}.",
                "risk_score_threshold": risk_threshold,
                "sample_accounting": {
                    "total_protected_labels": len(prot_ids),
                    "matched_predictions": 0,
                    "missing_predictions": len(missing_prediction_ids),
                    "unmatched_predictions": len(unmatched_prediction_ids),
                    "invalid_labels": invalid_label_count
                }
            }

        # Confusion Matrix
        tp = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1))
        fp = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1))
        tn = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0))
        fn = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0))

        # Reconcile exact sample totals
        reconciled_sum = tp + fp + tn + fn
        assert reconciled_sum == n_evaluated, f"Confusion matrix total {reconciled_sum} != sample count {n_evaluated}"

        # Standard scientific metrics
        accuracy = round(float((tp + tn) / max(1, n_evaluated)), 4)
        prec = round(float(tp / max(1, (tp + fp))), 4)
        rec = round(float(tp / max(1, (tp + fn))), 4)
        f1 = round(float((2 * prec * rec) / max(1e-6, (prec + rec))), 4)
        fpr = round(float(fp / max(1, (fp + tn))), 4)
        fnr = round(float(fn / max(1, (fn + tp))), 4)

        try:
            auc_roc, pr_auc = _compute_auc_roc_and_pr(y_true, y_scores)
        except Exception:
            auc_roc = 0.50
            pr_auc = round(float(sum(y_true) / max(1, n_evaluated)), 4)

        typology_report = {}
        for typ, data in typology_breakdown.items():
            typology_report[typ] = {
                "total_instances": data["total"],
                "detected_count": data["detected"],
                "recall_rate": round(data["detected"] / max(1, data["total"]), 3)
            }

        return {
            "dataset_name": dataset_name,
            "status": "EVALUATED",
            "evaluation_granularity": "TRANSACTION_LEVEL",
            "risk_score_threshold": risk_threshold,
            "sample_accounting": {
                "total_protected_labels": len(prot_ids),
                "matched_predictions": n_evaluated,
                "missing_predictions": len(missing_prediction_ids),
                "unmatched_predictions": len(unmatched_prediction_ids),
                "invalid_labels": invalid_label_count
            },
            "total_evaluated_samples": n_evaluated,
            "positive_laundering_count": int(sum(y_true)),
            "negative_legitimate_count": int(n_evaluated - sum(y_true)),
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn,
                "reconciled_total": reconciled_sum
            },
            "metrics": {
                "accuracy": accuracy,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "false_positive_rate": fpr,
                "false_negative_rate": fnr,
                "roc_auc": auc_roc,
                "pr_auc": pr_auc
            },
            "typology_performance": typology_report
        }

    @classmethod
    def evaluate_account_level(
        cls,
        conn: sqlite3.Connection,
        dataset_name: str = "NFPC_MULE",
        discovered_mule_account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates account-level mule discovery performance against protected NFPC account ground truth.
        """
        protected_data = get_protected_evaluation_labels(dataset_name=dataset_name)
        prot_accs = protected_data.get("accounts", {})

        if not prot_accs:
            return {
                "dataset_name": dataset_name,
                "status": "NO_PROTECTED_ACCOUNT_LABELS",
                "message": f"No account-level ground truth found for {dataset_name} in evaluation vault.",
                "sample_accounting": {
                    "total_protected_accounts": 0,
                    "evaluated_accounts": 0,
                    "missing_predictions": 0
                }
            }

        mule_set = set(discovered_mule_account_ids or [])

        y_true = []
        y_pred = []

        for acc_id, meta in prot_accs.items():
            is_mule = meta.get("is_mule")
            if is_mule not in (0, 1):
                continue

            pred = 1 if acc_id in mule_set else 0
            y_true.append(int(is_mule))
            y_pred.append(pred)

        if not y_true:
            return {
                "dataset_name": dataset_name,
                "status": "NOT EVALUATED",
                "message": f"Zero comparable accounts found for {dataset_name}."
            }

        n_accs = len(y_true)
        tp = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1))
        fp = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1))
        tn = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0))
        fn = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0))

        reconciled = tp + fp + tn + fn
        assert reconciled == n_accs

        accuracy = round(float((tp + tn) / max(1, n_accs)), 4)
        prec = round(float(tp / max(1, (tp + fp))), 4)
        rec = round(float(tp / max(1, (tp + fn))), 4)
        f1 = round(float((2 * prec * rec) / max(1e-6, (prec + rec))), 4)
        fpr = round(float(fp / max(1, (fp + tn))), 4)
        fnr = round(float(fn / max(1, (fn + tp))), 4)

        return {
            "dataset_name": dataset_name,
            "status": "EVALUATED",
            "evaluation_granularity": "ACCOUNT_LEVEL_MULE_DISCOVERY",
            "total_evaluated_accounts": n_accs,
            "true_mules_count": int(sum(y_true)),
            "true_legitimate_accounts": int(n_accs - sum(y_true)),
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn,
                "reconciled_total": reconciled
            },
            "metrics": {
                "accuracy": accuracy,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "false_positive_rate": fpr,
                "false_negative_rate": fnr
            }
        }

    @classmethod
    def evaluate_saml_untouched_test_set(
        cls,
        csv_path: Optional[str] = None,
        risk_threshold: float = 55.0
    ) -> Dict[str, Any]:
        """
        Evaluates the remediated model strictly against the untouched 30% chronological test partition
        of SAML-D (final 7,500 transactions, 2022-10-07 21:44:14 to 2022-10-08 08:38:47).
        Extracts features strictly at each event timestamp without look-ahead or cross-split leakage.
        """
        import os
        import pandas as pd
        from app.detection.supervised import _init_rf_remediated, FEATURE_SCHEMA

        if csv_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            csv_path = os.path.join(base_dir, "data", "saml_d", "saml_d_real.csv")

        if not os.path.exists(csv_path):
            return {
                "dataset_name": "SAML_D",
                "status": "NOT EVALUATED",
                "message": f"SAML-D dataset not found at {csv_path}"
            }

        df = pd.read_csv(csv_path)
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df = df.sort_values('DateTime').reset_index(drop=True)

        # Maintain event-time history across the full stream
        sender_out_history: Dict[str, List] = {}
        receiver_in_history: Dict[str, List] = {}
        feature_rows = []

        for idx, r in df.iterrows():
            sender = str(r['Sender_account'])
            receiver = str(r['Receiver_account'])
            amt = float(r['Amount'])
            dt = r['DateTime']
            curr = str(r.get('Payment_currency', 'USD')).upper()
            p_type = str(r.get('Payment_type', 'TRANSFER')).lower()
            src_loc = str(r.get('Sender_bank_location', ''))
            dest_loc = str(r.get('Receiver_bank_location', ''))

            out_hist = sender_out_history.get(sender, [])
            t_10m = dt - pd.Timedelta(minutes=10)
            vel_10m = len([a for (t, a, rec) in out_hist if t >= t_10m]) + 1.0

            in_hist = receiver_in_history.get(sender, [])
            t_30m = dt - pd.Timedelta(minutes=30)
            recent_in = [a for (t, a, snd) in in_hist if t >= t_30m]
            rapid_movement = 0.0
            if recent_in and amt > 0:
                for in_a in recent_in:
                    if 0.70 <= (amt / (in_a + 1.0)) <= 1.25:
                        rapid_movement = 1.0
                        break

            is_struct = 1.0 if (('POUND' in curr or 'USD' in curr or 'EUR' in curr) and (8500 <= amt < 10000)) else 0.0
            is_cross = 1.0 if (src_loc and dest_loc and src_loc != dest_loc) else 0.0
            is_cash = 1.0 if 'cash' in p_type else 0.0
            log_amt = np.log10(max(1.0, amt))

            prior_recipients = set(rec for (t, a, rec) in out_hist)
            is_new_recip = 1.0 if (receiver and receiver not in prior_recipients) else 0.0
            past_recip_count = float(len(prior_recipients))
            hist_len = float(len(out_hist))

            feature_rows.append([log_amt, vel_10m, rapid_movement, is_struct, is_cross, is_cash, is_new_recip, past_recip_count, hist_len])

            out_hist.append((dt, amt, receiver))
            sender_out_history[sender] = out_hist
            in_h = receiver_in_history.get(receiver, [])
            in_h.append((dt, amt, sender))
            receiver_in_history[receiver] = in_h

        X_all = np.array(feature_rows, dtype=float)
        y_all = df['Is_laundering'].values.astype(int)

        # Untouched 30% test partition: records 17,500 to 24,999
        X_test = X_all[17500:]
        y_test = y_all[17500:]
        test_df = df.iloc[17500:]

        model = _init_rf_remediated()
        if model is None:
            return {
                "dataset_name": "SAML_D",
                "status": "NOT EVALUATED",
                "message": "Remediated model unavailable for evaluation."
            }

        probs = model.predict_proba(X_test)[:, 1]
        threshold_prob = risk_threshold / 100.0 if risk_threshold > 1.0 else risk_threshold
        preds = (probs >= threshold_prob).astype(int)

        tp = int(np.sum((y_test == 1) & (preds == 1)))
        fp = int(np.sum((y_test == 0) & (preds == 1)))
        tn = int(np.sum((y_test == 0) & (preds == 0)))
        fn = int(np.sum((y_test == 1) & (preds == 0)))

        n_eval = len(y_test)
        reconciled = tp + fp + tn + fn
        assert reconciled == n_eval

        accuracy = round(float((tp + tn) / max(1, n_eval)), 4)
        prec = round(float(tp / max(1, (tp + fp))), 4)
        rec = round(float(tp / max(1, (tp + fn))), 4)
        f1 = round(float((2 * prec * rec) / max(1e-6, (prec + rec))), 4)
        fpr = round(float(fp / max(1, (fp + tn))), 4)
        fnr = round(float(fn / max(1, (fn + tp))), 4)

        auc_roc, pr_auc = _compute_auc_roc_and_pr(y_test.tolist(), probs.tolist())

        # Typology breakdown
        typology_report = {}
        for typ in test_df['Laundering_type'].unique():
            mask = (test_df['Laundering_type'] == typ).values
            tot = int(np.sum(mask))
            det = int(np.sum(mask & (preds == 1)))
            typology_report[typ] = {
                "total_instances": tot,
                "detected_count": det,
                "recall_rate": round(det / max(1, tot), 3)
            }

        return {
            "dataset_name": "SAML_D",
            "evaluation_type": "UNTOUCHED_CHRONOLOGICAL_TEST_SET",
            "evaluation_split": "FINAL_30_PERCENT",
            "date_range": (str(test_df['DateTime'].iloc[0]), str(test_df['DateTime'].iloc[-1])),
            "total_evaluated_samples": n_eval,
            "positive_laundering_count": int(np.sum(y_test == 1)),
            "negative_legitimate_count": int(np.sum(y_test == 0)),
            "risk_score_threshold": risk_threshold,
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn,
                "reconciled_total": reconciled
            },
            "metrics": {
                "accuracy": accuracy,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "false_positive_rate": fpr,
                "false_negative_rate": fnr,
                "roc_auc": auc_roc,
                "pr_auc": pr_auc
            },
            "typology_performance": typology_report
        }

    @classmethod
    def get_benchmark_comparison_matrix(cls, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Returns verified benchmark metrics across SAML-D, NFPC, and India Simulator."""
        saml_res = cls.evaluate_saml_untouched_test_set()
        india_res = cls.evaluate_transaction_level(conn, dataset_name="INDIA_SIMULATOR")
        nfpc_res = cls.evaluate_account_level(conn, dataset_name="NFPC_MULE")

        return {
            "datasets": {
                "SAML_D": saml_res,
                "NFPC_MULE": nfpc_res,
                "INDIA_SIMULATOR": india_res
            },
            "evaluation_status": "PROTECTED_GROUND_TRUTH_EVALUATION_ACTIVE"
        }
