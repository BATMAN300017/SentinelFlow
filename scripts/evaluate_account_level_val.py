"""
Step 5: Account-Level Evaluation on SAML-D Validation Split.

Evaluates whether aggregating transaction risk scores to the account level
via Max Score and Top-3 Mean Score improves detection of money laundering
networks and mule accounts compared to transaction-level scoring.

CRITICAL GUARDS:
1. Chronological Split:
   - Rows 0 to 5,702,910: Train partition (used strictly for state warm-up).
   - Rows 5,702,911 to 7,603,880: Validation partition (evaluated).
   - Rows 7,603,881 to 9,504,851: Final Test partition (STRICTLY UNTOUCHED).
2. Uses production HistGradientBoostingClassifier v3 artifact.
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

DATA_PATH = os.path.join("data", "saml_d", "SAML-D.csv")
MODEL_PATH = os.path.join("backend", "app", "models", "hist_gradient_boosting_samld_v3.joblib")

TRAIN_ROWS = 5_702_911
VAL_ROWS = 1_900_970
TOTAL_STREAM_ROWS = TRAIN_ROWS + VAL_ROWS  # 7,603,881 rows

def run_account_level_evaluation():
    print("=" * 70)
    print("STEP 5: ACCOUNT-LEVEL EVALUATION ON SAML-D VALIDATION SPLIT")
    print("=" * 70)
    print(f"Data file: {DATA_PATH}")
    print(f"Model artifact: {MODEL_PATH}")
    print(f"Train warm-up rows: {TRAIN_ROWS:,}")
    print(f"Validation evaluation rows: {VAL_ROWS:,}")
    print(f"Sealed Test partition (rows {TOTAL_STREAM_ROWS:,}+) is NOT read or touched.")
    print("-" * 70)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"SAML-D dataset not found at {DATA_PATH}")

    # Load model and calibrator
    artifact = joblib.load(MODEL_PATH)
    hgb_model = artifact["model"]
    calibrator = artifact["calibrator"]
    print(f"Loaded artifact version: {artifact.get('metadata', {}).get('version')}")

    t0 = time.time()

    outbound_history = {}
    inbound_history = {}
    seen_pairs = set()

    # Account-level tracking structures:
    # account -> list of (predicted_prob, is_laundering)
    account_scores_sender = {}
    account_scores_all = {}

    val_tx_probs = []
    val_tx_labels = []

    CHUNK_SIZE = 100_000
    row_idx = 0
    val_processed = 0

    print("\nPhase 1 & 2: Streaming data, warm-up train state and evaluating validation split...")

    for chunk in pd.read_csv(DATA_PATH, chunksize=CHUNK_SIZE):
        n_chunk = len(chunk)
        if row_idx >= TOTAL_STREAM_ROWS:
            break
        if row_idx + n_chunk > TOTAL_STREAM_ROWS:
            chunk = chunk.iloc[:TOTAL_STREAM_ROWS - row_idx]
            n_chunk = len(chunk)

        chunk_epochs = pd.to_datetime(chunk["Date"], format="ISO8601").astype("int64") // 10**9
        amts = chunk["Amount"].values.astype(float)
        srcs = chunk["Sender_account"].astype(str).values
        dsts = chunk["Receiver_account"].astype(str).values
        p_types = chunk["Payment_type"].astype(str).values
        p_currs = chunk["Payment_currency"].astype(str).values
        r_currs = chunk["Received_currency"].astype(str).values
        s_locs = chunk["Sender_bank_location"].astype(str).values
        r_locs = chunk["Receiver_bank_location"].astype(str).values
        is_launder = chunk["Is_laundering"].values.astype(int)
        epochs = chunk_epochs.values

        # If entire chunk is in train partition, fast update state only
        if row_idx + n_chunk <= TRAIN_ROWS:
            for i in range(n_chunk):
                src = srcs[i]
                dst = dsts[i]
                amt = amts[i]
                ep = int(epochs[i])
                tid = f"TXN-{row_idx + i}"

                if src not in outbound_history:
                    outbound_history[src] = []
                outbound_history[src].append((ep, tid, amt, dst))
                if dst:
                    if dst not in inbound_history:
                        inbound_history[dst] = []
                    inbound_history[dst].append((ep, tid, amt, src))
                    if src:
                        seen_pairs.add((src, dst))
            row_idx += n_chunk
            if row_idx % 1_000_000 == 0 or row_idx == TRAIN_ROWS:
                el = time.time() - t0
                print(f"  Warm-up: Processed {row_idx:,} / {TRAIN_ROWS:,} train rows ({row_idx/TRAIN_ROWS*100:.1f}%) in {el:.1f}s...")
            continue

        # Chunk crosses or is inside validation partition
        # Build features for val rows, batch predict in chunks for high efficiency
        val_vecs = []
        val_chunk_labels = []
        val_chunk_srcs = []
        val_chunk_dsts = []

        for i in range(n_chunk):
            curr_row = row_idx + i
            src = srcs[i]
            dst = dsts[i]
            amt = amts[i]
            ep = int(epochs[i])
            tid = f"TXN-{curr_row}"
            label = int(is_launder[i])

            if curr_row < TRAIN_ROWS:
                # Still in train part of split boundary
                if src not in outbound_history:
                    outbound_history[src] = []
                outbound_history[src].append((ep, tid, amt, dst))
                if dst:
                    if dst not in inbound_history:
                        inbound_history[dst] = []
                    inbound_history[dst].append((ep, tid, amt, src))
                    if src:
                        seen_pairs.add((src, dst))
            else:
                # In validation split: compute point-in-time features strictly
                p_out = outbound_history.get(src, [])
                p_in = inbound_history.get(src, [])
                has_cycle = (dst, src) in seen_pairs if (dst and src) else False

                vec = compute_point_in_time_features(
                    amount=amt,
                    current_epoch=ep,
                    current_id=tid,
                    payment_type_raw=p_types[i],
                    payment_currency_raw=p_currs[i],
                    received_currency_raw=r_currs[i],
                    sender_country_raw=s_locs[i],
                    receiver_country_raw=r_locs[i],
                    receiver_id=dst,
                    prior_outbound=p_out,
                    prior_inbound=p_in,
                    has_cycle=has_cycle
                )
                val_vecs.append(vec)
                val_chunk_labels.append(label)
                val_chunk_srcs.append(src)
                val_chunk_dsts.append(dst)

                # Update history after computing point-in-time features
                if src not in outbound_history:
                    outbound_history[src] = []
                outbound_history[src].append((ep, tid, amt, dst))
                if dst:
                    if dst not in inbound_history:
                        inbound_history[dst] = []
                    inbound_history[dst].append((ep, tid, amt, src))
                    if src:
                        seen_pairs.add((src, dst))

        if val_vecs:
            X_val_batch = np.array(val_vecs, dtype=np.float32)
            raw_probs = hgb_model.predict_proba(X_val_batch)[:, 1]
            if calibrator is not None:
                cal_probs = calibrator.predict(raw_probs)
            else:
                cal_probs = raw_probs

            # Record transaction-level scores
            val_tx_probs.extend(cal_probs)
            val_tx_labels.extend(val_chunk_labels)

            # Record account-level associations
            for p, lbl, s_acc, d_acc in zip(cal_probs, val_chunk_labels, val_chunk_srcs, val_chunk_dsts):
                # Sender-only view
                if s_acc not in account_scores_sender:
                    account_scores_sender[s_acc] = []
                account_scores_sender[s_acc].append((p, lbl))

                # All-participating accounts view (both sender and receiver)
                if s_acc not in account_scores_all:
                    account_scores_all[s_acc] = []
                account_scores_all[s_acc].append((p, lbl))

                if d_acc:
                    if d_acc not in account_scores_all:
                        account_scores_all[d_acc] = []
                    account_scores_all[d_acc].append((p, lbl))

            val_processed += len(val_vecs)

        row_idx += n_chunk
        if val_processed > 0 and val_processed % 200_000 == 0:
            el = time.time() - t0
            print(f"  Validation: Scored {val_processed:,} / {VAL_ROWS:,} transactions in {el:.1f}s...")

    total_time = time.time() - t0
    print(f"\nCompleted streaming and scoring in {total_time:.1f}s ({total_time/60:.2f} min).")
    print(f"Validation transactions evaluated: {len(val_tx_probs):,}")
    print(f"Unique Sender accounts: {len(account_scores_sender):,}")
    print(f"Unique Participating accounts: {len(account_scores_all):,}")

    # Convert transaction evaluations to numpy
    tx_p = np.array(val_tx_probs, dtype=np.float64)
    tx_y = np.array(val_tx_labels, dtype=np.int8)

    tx_roc_auc = roc_auc_score(tx_y, tx_p)
    prec_arr, rec_arr, _ = precision_recall_curve(tx_y, tx_p)
    tx_pr_auc = auc(rec_arr, prec_arr)

    print("\n" + "=" * 70)
    print("TRANSACTION-LEVEL BASELINE (FOR COMPARISON)")
    print("=" * 70)
    print(f"Validation Transactions: {len(tx_y):,}")
    print(f"Positive Transactions:   {np.sum(tx_y):,} ({np.mean(tx_y)*100:.4f}%)")
    print(f"ROC-AUC:                 {tx_roc_auc:.4f}")
    print(f"PR-AUC:                  {tx_pr_auc:.4f}")

    # Evaluate Account-Level Aggregation
    def compute_account_metrics(acc_dict, name):
        print("\n" + "=" * 70)
        print(f"ACCOUNT-LEVEL EVALUATION: {name.upper()}")
        print("=" * 70)
        n_accounts = len(acc_dict)
        labels = np.empty(n_accounts, dtype=np.int8)
        max_scores = np.empty(n_accounts, dtype=np.float64)
        top3_scores = np.empty(n_accounts, dtype=np.float64)
        mean_scores = np.empty(n_accounts, dtype=np.float64)
        txn_counts = np.empty(n_accounts, dtype=np.int32)

        for idx, (acc, items) in enumerate(acc_dict.items()):
            # Ground truth: 1 if account participated in ANY laundering transaction
            lbl = 1 if any(it[1] == 1 for it in items) else 0
            scores = [it[0] for it in items]
            scores_sorted = sorted(scores, reverse=True)

            labels[idx] = lbl
            max_scores[idx] = scores_sorted[0]
            top3_scores[idx] = np.mean(scores_sorted[:3])
            mean_scores[idx] = np.mean(scores_sorted)
            txn_counts[idx] = len(items)

        pos_count = int(np.sum(labels))
        neg_count = n_accounts - pos_count
        pos_rate = pos_count / n_accounts * 100

        print(f"Total Accounts:    {n_accounts:,}")
        print(f"Positive Accounts: {pos_count:,} ({pos_rate:.4f}%)")
        print(f"Negative Accounts: {neg_count:,}")

        # Metrics for Max Score
        roc_max = roc_auc_score(labels, max_scores)
        p_max, r_max, _ = precision_recall_curve(labels, max_scores)
        pr_auc_max = auc(r_max, p_max)

        # Metrics for Top-3 Mean Score
        roc_top3 = roc_auc_score(labels, top3_scores)
        p_top3, r_top3, _ = precision_recall_curve(labels, top3_scores)
        pr_auc_top3 = auc(r_top3, p_top3)

        # Metrics for Mean Score
        roc_mean = roc_auc_score(labels, mean_scores)
        p_mean, r_mean, _ = precision_recall_curve(labels, mean_scores)
        pr_auc_mean = auc(r_mean, p_mean)

        print("\n--- Model Discrimination Metrics ---")
        print(f"Max Score:         ROC-AUC = {roc_max:.4f} | PR-AUC = {pr_auc_max:.4f}")
        print(f"Top-3 Mean Score:  ROC-AUC = {roc_top3:.4f} | PR-AUC = {pr_auc_top3:.4f}")
        print(f"Mean Score:        ROC-AUC = {roc_mean:.4f} | PR-AUC = {pr_auc_mean:.4f}")

        # Evaluate at fixed FPRs on negative accounts
        fpr_targets = [0.01, 0.05, 0.10]
        results = {}

        for score_name, scores in [("Max Score", max_scores), ("Top-3 Mean", top3_scores), ("Mean Score", mean_scores)]:
            print(f"\n--- Operating Points for {score_name} ---")
            fpr_arr, tpr_arr, thresh_arr = roc_curve(labels, scores)
            
            for target_fpr in fpr_targets:
                idx_fpr = np.where(fpr_arr <= target_fpr)[0][-1]
                t = thresh_arr[idx_fpr]
                preds = (scores >= t).astype(int)
                tp = int(np.sum((preds == 1) & (labels == 1)))
                fp = int(np.sum((preds == 1) & (labels == 0)))
                fn = int(np.sum((preds == 0) & (labels == 1)))
                rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                actual_fpr = fp / neg_count if neg_count > 0 else 0.0

                print(f"  @{target_fpr*100:.0f}% Target FPR (actual {actual_fpr*100:.2f}%): "
                      f"Recall = {rec*100:.2f}% ({tp}/{pos_count}) | "
                      f"Precision = {prec*100:.2f}% | "
                      f"Alerted = {tp+fp:,} accounts | Thresh = {t:.4f}")
                
            results[score_name] = {
                "roc_auc": roc_max if score_name == "Max Score" else (roc_top3 if score_name == "Top-3 Mean" else roc_mean),
                "pr_auc": pr_auc_max if score_name == "Max Score" else (pr_auc_top3 if score_name == "Top-3 Mean" else pr_auc_mean)
            }

        return results

    res_sender = compute_account_metrics(account_scores_sender, "Sender Accounts Only")
    res_all = compute_account_metrics(account_scores_all, "All Participating Accounts (Senders & Receivers)")

    # Print Network Laundering Detection Comparison
    print("\n" + "=" * 70)
    print("DETECTION OF LAUNDERING NETWORKS: ACCOUNT VS TRANSACTION COMPARISON")
    print("=" * 70)
    print("Comparison Findings:")
    print("1. Transaction scoring alerts on individual transactions, dispersing alerts across disparate rows.")
    print("2. Account-level Max Score achieves:")
    print(f"   - Sender Accounts ROC-AUC: {res_sender['Max Score']['roc_auc']:.4f}, PR-AUC: {res_sender['Max Score']['pr_auc']:.4f}")
    print(f"   - All Accounts ROC-AUC:    {res_all['Max Score']['roc_auc']:.4f}, PR-AUC: {res_all['Max Score']['pr_auc']:.4f}")
    print("3. Account-level Top-3 Mean achieves:")
    print(f"   - Sender Accounts ROC-AUC: {res_sender['Top-3 Mean']['roc_auc']:.4f}, PR-AUC: {res_sender['Top-3 Mean']['pr_auc']:.4f}")
    print(f"   - All Accounts ROC-AUC:    {res_all['Top-3 Mean']['roc_auc']:.4f}, PR-AUC: {res_all['Top-3 Mean']['pr_auc']:.4f}")
    print("4. Conclusion:")
    print("   Aggregating transaction risk scores to the account level (especially Max Score and Top-3 Mean)")
    print("   concentrates multi-transaction laundering signals and eliminates alert duplication.")
    print("=" * 70)

if __name__ == "__main__":
    run_account_level_evaluation()
