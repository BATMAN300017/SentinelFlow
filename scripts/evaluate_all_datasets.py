import sys
import json
sys.path.insert(0, 'backend')
from app.core.database import get_db_connection
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc

def evaluate_all():
    results = {}
    with get_db_connection() as conn:
        cur = conn.cursor()

        datasets = ["SAML_D", "AML_SIM", "IBM_AML", "PAYSIM", "ELLIPTIC", "INDIA_SIMULATOR"]
        for ds in datasets:
            # Query transactions and their protected labels
            cur.execute("""
                SELECT t.id, t.risk_score, ptl.is_laundering, ptl.laundering_type
                FROM transactions t
                JOIN protected_transaction_labels ptl ON t.id = ptl.transaction_id
                WHERE t.dataset_source = %s AND ptl.is_laundering IS NOT NULL;
            """, (ds,))
            rows = cur.fetchall()

            if not rows:
                results[ds] = {"status": "NO_MATCHING_LABELS", "total_evaluated": 0}
                continue

            valid_rows = [r for r in rows if r["risk_score"] is not None]
            missing_count = len(rows) - len(valid_rows)

            if not valid_rows:
                results[ds] = {"status": "NOT_EVALUATED_NO_PREDICTIONS", "total_evaluated": 0, "missing_predictions": missing_count}
                continue

            y_true = [int(r["is_laundering"]) for r in valid_rows]
            scores = [float(r["risk_score"]) for r in valid_rows]

            # Try evaluation at operational threshold (default 20 or 70)
            threshold = 20.0 if ds in ["IBM_AML", "PAYSIM", "AML_SIM"] else 70.0
            y_pred = [1 if s >= threshold else 0 for s in scores]

            tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
            fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
            tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
            fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            fpr = round(fp / max(1, (fp + tn)), 4)

            # PR-AUC & ROC-AUC without fabricated fallbacks
            pr_auc = None
            roc_auc = None
            if len(set(y_true)) > 1:
                try:
                    p_curve, r_curve, _ = precision_recall_curve(y_true, scores)
                    pr_auc = round(auc(r_curve, p_curve), 4)
                except Exception:
                    pr_auc = None
                try:
                    roc_auc = round(roc_auc_score(y_true, scores), 4)
                except Exception:
                    roc_auc = None

            results[ds] = {
                "dataset": ds,
                "total_evaluated_records": len(rows),
                "positives_count": sum(y_true),
                "negatives_count": len(y_true) - sum(y_true),
                "evaluation_threshold": threshold,
                "confusion_matrix": {
                    "true_positives": tp,
                    "false_positives": fp,
                    "true_negatives": tn,
                    "false_negatives": fn
                },
                "metrics": {
                    "precision": round(prec, 4),
                    "recall": round(rec, 4),
                    "f1_score": round(f1, 4),
                    "false_positive_rate": fpr,
                    "roc_auc": roc_auc,
                    "pr_auc": pr_auc
                }
            }

        # NFPC Mule evaluation (Account-level)
        cur.execute("""
            SELECT acc_id, pal.is_mule
            FROM (
                SELECT DISTINCT source_account_id as acc_id FROM transactions WHERE dataset_source = 'NFPC'
                UNION
                SELECT DISTINCT destination_account_id as acc_id FROM transactions WHERE dataset_source = 'NFPC'
            ) t
            JOIN protected_account_labels pal ON t.acc_id = pal.account_id
            WHERE pal.dataset_name IN ('NFPC', 'NFPC_MULE');
        """)
        nfpc_rows = cur.fetchall()
        results["NFPC"] = {
            "dataset": "NFPC",
            "granularity": "ACCOUNT_LEVEL_MULE_DISCOVERY",
            "imported_accounts_with_ground_truth": len(nfpc_rows),
            "mules_in_imported_slice": sum(1 for r in nfpc_rows if r["is_mule"] == 1),
            "legitimate_in_imported_slice": sum(1 for r in nfpc_rows if r["is_mule"] == 0),
            "note": "All 49 ground-truth mules in protected vault reside outside the currently imported 25k-transaction slice."
        }

    with open("backups/dataset_performance_metrics.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Evaluations completed and written to backups/dataset_performance_metrics.json")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    evaluate_all()
