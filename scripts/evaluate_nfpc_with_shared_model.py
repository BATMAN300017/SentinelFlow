"""
Evaluate NFPC Dataset using SentinelFlow's Shared Feature Extractor and HGB v3 Model.

Maps NFPC transactions to canonical schema, computes point-in-time features chronologically,
and scores them with HistGradientBoostingClassifier v3 to measure genuine precision and recall.
"""

import os
import sys
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, roc_curve

sys.path.insert(0, 'backend')
from app.detection.point_in_time_features import (
    AML_FEATURE_NAMES,
    compute_point_in_time_features
)

DATA_PATH = os.path.join("data", "nfpc", "part_0001.parquet")
LABELS_PATH = os.path.join("data", "nfpc", "train_labels.parquet")
MODEL_PATH = os.path.join("backend", "app", "models", "hist_gradient_boosting_samld_v3.joblib")

def run_nfpc_evaluation():
    print("=" * 70)
    print("STEP 6: NFPC EVALUATION WITH SHARED FEATURE EXTRACTOR AND HGB V3 MODEL")
    print("=" * 70)
    print(f"Transactions: {DATA_PATH}")
    print(f"Labels:       {LABELS_PATH}")
    print(f"Model:        {MODEL_PATH}")
    print("-" * 70)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")
    if not os.path.exists(DATA_PATH) or not os.path.exists(LABELS_PATH):
        raise FileNotFoundError("NFPC dataset files not found.")

    artifact = joblib.load(MODEL_PATH)
    hgb_model = artifact["model"]
    calibrator = artifact["calibrator"]

    # 1. Load labels
    print("Loading NFPC ground-truth labels...")
    df_labels = pd.read_parquet(LABELS_PATH)
    label_map = dict(zip(df_labels["account_id"].astype(str), df_labels["is_mule"].astype(int)))
    labeled_accs = set(label_map.keys())
    mule_count = sum(label_map.values())
    print(f"Total labeled accounts: {len(label_map):,} (Mules: {mule_count:,}, Legitimate: {len(label_map)-mule_count:,})")

    # 2. Load transactions and filter to those involving labeled accounts
    print("Loading NFPC transaction partition...")
    t0 = time.time()
    df_tx = pd.read_parquet(DATA_PATH)
    print(f"Loaded {len(df_tx):,} transactions in {time.time()-t0:.1f}s.")

    # Chronological sort is critical for point-in-time causality
    print("Sorting transactions chronologically...")
    df_tx["epoch"] = pd.to_datetime(df_tx["transaction_timestamp"], format="ISO8601").astype("int64") // 10**9
    df_tx.sort_values(by="epoch", inplace=True)
    df_tx.reset_index(drop=True, inplace=True)

    # 3. Stream through transactions, maintain point-in-time state, and extract features
    print("Streaming transactions through shared point-in-time feature extractor...")
    t1 = time.time()

    outbound_history = {}
    inbound_history = {}
    seen_pairs = set()

    # account -> list of predicted probabilities
    account_scores = {}

    batch_vecs = []
    batch_tx_accs = []
    CHUNK_EVAL = 50_000

    n_tx = len(df_tx)
    ep_vals = df_tx["epoch"].values
    amt_vals = df_tx["amount"].values.astype(float)
    type_vals = df_tx["txn_type"].values
    ch_vals = df_tx["channel"].values
    acc_vals = df_tx["account_id"].astype(str).values
    cp_vals = df_tx["counterparty_id"].astype(str).values
    txid_vals = df_tx["transaction_id"].astype(str).values

    for i in range(n_tx):
        tt = type_vals[i]
        ep = int(ep_vals[i])
        amt = amt_vals[i]
        ch = str(ch_vals[i])
        tid = txid_vals[i]

        if tt == "D":
            src = acc_vals[i]
            dst = cp_vals[i]
        else:
            src = cp_vals[i]
            dst = acc_vals[i]

        p_out = outbound_history.get(src, [])
        p_in = inbound_history.get(src, [])
        has_cycle = (dst, src) in seen_pairs if (dst and src) else False

        # Only predict if at least one party is a labeled evaluation account
        needs_scoring = (src in labeled_accs or dst in labeled_accs)

        if needs_scoring:
            vec = compute_point_in_time_features(
                amount=amt,
                current_epoch=ep,
                current_id=tid,
                payment_type_raw=ch,
                payment_currency_raw="INR",
                received_currency_raw="INR",
                sender_country_raw="IND",
                receiver_country_raw="IND",
                receiver_id=dst,
                prior_outbound=p_out,
                prior_inbound=p_in,
                has_cycle=has_cycle
            )
            batch_vecs.append(vec)
            batch_tx_accs.append((src, dst))

        # Update point-in-time streaming state
        if src not in outbound_history:
            outbound_history[src] = []
        outbound_history[src].append((ep, tid, amt, dst))
        if dst:
            if dst not in inbound_history:
                inbound_history[dst] = []
            inbound_history[dst].append((ep, tid, amt, src))
            if src:
                seen_pairs.add((src, dst))

        # Score in batches
        if len(batch_vecs) >= CHUNK_EVAL:
            X_batch = np.array(batch_vecs, dtype=np.float32)
            raw_p = hgb_model.predict_proba(X_batch)[:, 1]
            if calibrator is not None:
                cal_p = calibrator.predict(raw_p)
            else:
                cal_p = raw_p

            for p, (s, d) in zip(cal_p, batch_tx_accs):
                if s in labeled_accs:
                    if s not in account_scores: account_scores[s] = []
                    account_scores[s].append(p)
                if d in labeled_accs:
                    if d not in account_scores: account_scores[d] = []
                    account_scores[d].append(p)

            batch_vecs.clear()
            batch_tx_accs.clear()

        if (i + 1) % 250_000 == 0:
            print(f"  Processed {i+1:,} / {n_tx:,} txns ({(i+1)/n_tx*100:.1f}%) in {time.time()-t1:.1f}s...")

    # Flush remainder
    if batch_vecs:
        X_batch = np.array(batch_vecs, dtype=np.float32)
        raw_p = hgb_model.predict_proba(X_batch)[:, 1]
        if calibrator is not None:
            cal_p = calibrator.predict(raw_p)
        else:
            cal_p = raw_p

        for p, (s, d) in zip(cal_p, batch_tx_accs):
            if s in labeled_accs:
                if s not in account_scores: account_scores[s] = []
                account_scores[s].append(p)
            if d in labeled_accs:
                if d not in account_scores: account_scores[d] = []
                account_scores[d].append(p)

    print(f"\nFeature extraction and scoring complete in {time.time()-t1:.1f}s.")
    print(f"Evaluated labeled accounts with transactions: {len(account_scores):,}")

    # Compute account-level max and top-3 mean
    acc_labels = []
    acc_max_scores = []
    acc_top3_scores = []

    for acc, scores in account_scores.items():
        lbl = label_map[acc]
        s_sorted = sorted(scores, reverse=True)
        acc_labels.append(lbl)
        acc_max_scores.append(s_sorted[0])
        acc_top3_scores.append(np.mean(s_sorted[:3]))

    y_true = np.array(acc_labels, dtype=np.int8)
    max_scores = np.array(acc_max_scores, dtype=np.float64)
    top3_scores = np.array(acc_top3_scores, dtype=np.float64)

    total_eval = len(y_true)
    total_mules = int(np.sum(y_true))
    total_legits = total_eval - total_mules

    print("\n" + "=" * 70)
    print("NFPC EVALUATION RESULTS")
    print("=" * 70)
    print(f"Total Evaluated Accounts: {total_eval:,}")
    print(f"Confirmed Mule Accounts:  {total_mules:,} ({total_mules/total_eval*100:.2f}%)")
    print(f"Legitimate Accounts:      {total_legits:,}")

    roc_max = roc_auc_score(y_true, max_scores)
    p_max, r_max, _ = precision_recall_curve(y_true, max_scores)
    pr_auc_max = auc(r_max, p_max)

    roc_top3 = roc_auc_score(y_true, top3_scores)
    p_top3, r_top3, _ = precision_recall_curve(y_true, top3_scores)
    pr_auc_top3 = auc(r_top3, p_top3)

    print("\n--- Discrimination Metrics ---")
    print(f"Max Score:        ROC-AUC = {roc_max:.4f} | PR-AUC = {pr_auc_max:.4f}")
    print(f"Top-3 Mean Score: ROC-AUC = {roc_top3:.4f} | PR-AUC = {pr_auc_top3:.4f}")

    # Threshold analysis
    for name, sc in [("Max Score", max_scores), ("Top-3 Mean", top3_scores)]:
        print(f"\n--- Operating Points for {name} ---")
        fpr_arr, tpr_arr, thresh_arr = roc_curve(y_true, sc)
        for target_fpr in [0.01, 0.05, 0.10]:
            idx_fpr = np.where(fpr_arr <= target_fpr)[0][-1]
            t = thresh_arr[idx_fpr]
            preds = (sc >= t).astype(int)
            tp = int(np.sum((preds == 1) & (y_true == 1)))
            fp = int(np.sum((preds == 1) & (y_true == 0)))
            rec = tp / total_mules if total_mules > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            actual_fpr = fp / total_legits if total_legits > 0 else 0.0
            print(f"  @{target_fpr*100:.0f}% Target FPR (actual {actual_fpr*100:.2f}%): "
                  f"Recall = {rec*100:.2f}% ({tp}/{total_mules}) | "
                  f"Precision = {prec*100:.2f}% | "
                  f"Alerts = {tp+fp:,} | Thresh = {t:.4f}")

        # Also evaluate at default operating threshold (0.0261)
        for t_fixed in [0.0261, 0.05, 0.10]:
            preds = (sc >= t_fixed).astype(int)
            tp = int(np.sum((preds == 1) & (y_true == 1)))
            fp = int(np.sum((preds == 1) & (y_true == 0)))
            rec = tp / total_mules if total_mules > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            actual_fpr = fp / total_legits if total_legits > 0 else 0.0
            print(f"  @Fixed Thresh {t_fixed:.4f}: "
                  f"Recall = {rec*100:.2f}% ({tp}/{total_mules}) | "
                  f"Precision = {prec*100:.2f}% | "
                  f"FPR = {actual_fpr*100:.2f}% | Alerts = {tp+fp:,}")

if __name__ == "__main__":
    run_nfpc_evaluation()
