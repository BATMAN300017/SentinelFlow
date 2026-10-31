import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import get_db_connection
from app.data_ingestion.label_isolation import get_protected_evaluation_labels
from app.detection.features import extract_transaction_features
from app.detection.rules import evaluate_rules
from app.detection.anomaly import calculate_mad_anomaly
from app.detection.isolation_forest import get_isolation_forest_score
from app.detection.graph_signals import evaluate_graph_signals
from app.detection.supervised import predict_supervised_risk
from app.detection.ensemble import compute_ensemble_risk

from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

def compare_models():
    prot = get_protected_evaluation_labels("SAML_D")
    prot_txns = prot.get("transactions", {})
    if not prot_txns:
        print("No protected transactions found.")
        return

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, created_at, risk_score
            FROM transactions
            WHERE dataset_source = 'SAML_D'
            LIMIT 200;
        """)
        txns = cur.fetchall()
        print(f"Sampled {len(txns)} transactions for identical split comparison.")

        y_true = []
        valid_txns = []
        for t in txns:
            tid = t["id"]
            if tid in prot_txns:
                lbl = prot_txns[tid].get("is_laundering")
                if lbl is not None:
                    y_true.append(lbl)
                    valid_txns.append(dict(t))

        print(f"Valid labeled samples: {len(valid_txns)}, positives: {sum(y_true)}")

        model_scores = {
            "rules": [],
            "mad_anomaly": [],
            "isolation_forest": [],
            "graph_centrality": [],
            "random_forest": [],
            "ensemble": []
        }
        latencies = {k: 0.0 for k in model_scores}

        for txn in valid_txns:
            features = extract_transaction_features(conn, txn)

            # 1. Rules
            t0 = time.perf_counter()
            triggered_rules = evaluate_rules(conn, txn, features)
            rule_score = min(100.0, sum(r["score_contribution"] for r in triggered_rules))
            latencies["rules"] += (time.perf_counter() - t0)
            model_scores["rules"].append(rule_score)

            # 2. MAD
            t0 = time.perf_counter()
            historical_amounts = features.get("historical_amounts", [])
            is_cold = bool(features.get("is_cold_start", 0))
            anomaly_res = calculate_mad_anomaly(float(txn["amount"]), historical_amounts, is_cold)
            anomaly_score = anomaly_res["score"]
            latencies["mad_anomaly"] += (time.perf_counter() - t0)
            model_scores["mad_anomaly"].append(anomaly_score)

            # 3. IF
            t0 = time.perf_counter()
            if_res = get_isolation_forest_score(features)
            isolation_forest_score = if_res.get("isolation_forest_score", 0.0)
            latencies["isolation_forest"] += (time.perf_counter() - t0)
            model_scores["isolation_forest"].append(isolation_forest_score)

            # 4. Graph
            t0 = time.perf_counter()
            graph_res = evaluate_graph_signals(conn, txn)
            graph_score = graph_res["graph_score"]
            latencies["graph_centrality"] += (time.perf_counter() - t0)
            model_scores["graph_centrality"].append(graph_score)

            # 5. RF Supervised
            t0 = time.perf_counter()
            sup_res = predict_supervised_risk(features)
            supervised_score = sup_res["supervised_score"]
            latencies["random_forest"] += (time.perf_counter() - t0)
            model_scores["random_forest"].append(supervised_score)

            # 6. Ensemble
            t0 = time.perf_counter()
            ens_res = compute_ensemble_risk(
                rule_score=rule_score,
                anomaly_score=anomaly_score,
                supervised_score=supervised_score,
                graph_score=graph_score,
                isolation_forest_score=isolation_forest_score
            )
            ens_score = float(ens_res.get("final_risk_score", 0.0))
            latencies["ensemble"] += (time.perf_counter() - t0)
            model_scores["ensemble"].append(ens_score)

        print("\n--- Model Comparison on Identical Evaluation Split ---")
        N = len(valid_txns)
        for m_name, scores in model_scores.items():
            preds = [1 if s >= 50.0 else 0 for s in scores]
            prob_scores = [s / 100.0 for s in scores]

            prec = precision_score(y_true, preds, zero_division=0)
            rec = recall_score(y_true, preds, zero_division=0)
            f1 = f1_score(y_true, preds, zero_division=0)
            tp = sum(1 for yt, yp in zip(y_true, preds) if yt == 1 and yp == 1)
            fp = sum(1 for yt, yp in zip(y_true, preds) if yt == 0 and yp == 1)
            tn = sum(1 for yt, yp in zip(y_true, preds) if yt == 0 and yp == 0)
            fn = sum(1 for yt, yp in zip(y_true, preds) if yt == 1 and yp == 0)
            fpr = round(fp / max(1, (fp + tn)), 4)
            try:
                roc = round(roc_auc_score(y_true, prob_scores), 4)
                pr_auc = round(average_precision_score(y_true, prob_scores), 4)
            except Exception:
                roc = 0.50
                pr_auc = 0.50

            avg_latency_ms = round((latencies[m_name] / max(1, N)) * 1000.0, 2)

            print(f"{m_name:18} | Prec: {prec:.3f} | Rec: {rec:.3f} | F1: {f1:.3f} | PR-AUC: {pr_auc:.3f} | ROC-AUC: {roc:.3f} | FPR: {fpr:.3f} | Latency: {avg_latency_ms}ms")

if __name__ == "__main__":
    compare_models()
