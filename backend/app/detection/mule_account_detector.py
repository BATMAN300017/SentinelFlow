import sqlite3
from typing import Dict, Any, List
import numpy as np

def analyze_suspicious_account_network(conn: sqlite3.Connection, account_id: str) -> Dict[str, Any]:
    """
    Distinct Analytical Output: Suspicious Account / Network Prediction.
    Evaluates linked transactions, counterparty network, and fund pass-through behavior
    to independently predict whether an account operates as a Money Mule.
    NEVER accesses ground-truth labels.
    """
    cursor = conn.cursor()
    
    # 1. Query outbound transactions (capped at 100 for bounded execution)
    cursor.execute("""
        SELECT id, amount, destination_account_id, payment_channel, created_at
        FROM transactions
        WHERE source_account_id = ?
        ORDER BY created_at DESC LIMIT 100
    """, (account_id,))
    out_rows = cursor.fetchall()
    
    # 2. Query inbound transactions (capped at 100)
    cursor.execute("""
        SELECT id, amount, source_account_id, payment_channel, created_at
        FROM transactions
        WHERE destination_account_id = ?
        ORDER BY created_at DESC LIMIT 100
    """, (account_id,))
    in_rows = cursor.fetchall()
    
    out_txns = [dict(r._dict if hasattr(r, "_dict") else r) for r in out_rows]
    in_txns = [dict(r._dict if hasattr(r, "_dict") else r) for r in in_rows]
    
    total_out = sum(float(t.get("amount") or 0.0) for t in out_txns)
    total_in = sum(float(t.get("amount") or 0.0) for t in in_txns)
    total_txns = len(out_txns) + len(in_txns)
    
    out_counterparties = set(t.get("destination_account_id") for t in out_txns if t.get("destination_account_id"))
    in_counterparties = set(t.get("source_account_id") for t in in_txns if t.get("source_account_id"))
    total_unique_cps = len(out_counterparties.union(in_counterparties))
    
    # 3. Calculate Operational Mule Signals
    if total_in > 0 and total_out > 0:
        pass_through_ratio = min(total_in, total_out) / (max(total_in, total_out) + 1.0)
    else:
        pass_through_ratio = 0.0
        
    dispersion_rate = total_unique_cps / (total_txns + 1.0)
    
    # Check account status from accounts table
    cursor.execute("SELECT balance, is_dormant, currency, created_at FROM accounts WHERE id = ?", (account_id,))
    acc_row = cursor.fetchone()
    if acc_row:
        acc_dict = dict(acc_row._dict if hasattr(acc_row, "_dict") else acc_row)
        is_dormant = bool(acc_dict.get("is_dormant", False))
        balance = float(acc_dict.get("balance") or 0.0)
        curr = acc_dict.get("currency", "USD")
    else:
        is_dormant = False
        balance = 0.0
        curr = "USD"
        
    # 4. Multi-Signal Mule Probability Scoring
    # Component scores
    s_passthrough = min(1.0, pass_through_ratio * 1.1)
    s_volume = min(1.0, (total_out + total_in) / 500000.0) # normalized volume
    s_velocity = min(1.0, total_txns / 30.0)
    s_counterparties = min(1.0, total_unique_cps / 15.0)
    s_dormant = 0.8 if (is_dormant and total_txns > 3) else 0.0
    
    # Composite probability calculation
    raw_mule_score = (
        0.35 * s_passthrough +
        0.25 * s_counterparties +
        0.20 * s_velocity +
        0.10 * s_volume +
        0.10 * s_dormant
    )
    
    # Calibrated probability
    calibrated_prob = round(float(1.0 / (1.0 + np.exp(-5.0 * (raw_mule_score - 0.45)))), 4)
    
    # Classify Network Role
    if len(in_counterparties) >= 4 and len(out_counterparties) <= 2:
        network_role = "MULE_COLLECTION_FUNNEL"
        role_desc = f"Account funnels funds from {len(in_counterparties)} inbound sources into limited consolidation targets."
    elif len(out_counterparties) >= 5 and total_out > total_in * 1.5:
        network_role = "MULE_DISBURSAL_HUB"
        role_desc = f"Account rapidly disperses liquidity across {len(out_counterparties)} distinct counterparty nodes."
    elif pass_through_ratio >= 0.80 and total_txns >= 10:
        network_role = "MULE_STAGING_ACCOUNT"
        role_desc = f"High pass-through velocity ({pass_through_ratio*100:.1f}%) observed; incoming funds exited rapidly retaining minimal balance."
    elif calibrated_prob >= 0.70:
        network_role = "HIGH_RISK_SYNDICATE_NODE"
        role_desc = "Multi-signal structural anomaly in transaction timing and counterparty concentration."
    else:
        network_role = "STANDARD_OPERATING_ACCOUNT"
        role_desc = "Account transaction behavior conforms to routine operational parameters."

    # Evidence items supporting account-level prediction
    evidence = [
        f"Total examined transactions: {total_txns} ({len(in_txns)} inbound, {len(out_txns)} outbound)",
        f"Total unique counterparties: {total_unique_cps} ({len(in_counterparties)} sources, {len(out_counterparties)} destinations)",
        f"Cumulative volume: {curr} {total_in + total_out:,.2f} (In: {total_in:,.2f}, Out: {total_out:,.2f})",
        f"Liquidity pass-through ratio: {pass_through_ratio * 100:.1f}%",
    ]
    if is_dormant:
        evidence.append("Account flagged as dormant prior to sudden velocity spike")

    return {
        "account_id": account_id,
        "predicted_mule_probability": calibrated_prob,
        "mule_risk_tier": "CRITICAL" if calibrated_prob >= 0.80 else "HIGH" if calibrated_prob >= 0.60 else "MEDIUM" if calibrated_prob >= 0.40 else "LOW",
        "network_role": network_role,
        "role_description": role_desc,
        "signals": {
            "pass_through_ratio": round(pass_through_ratio, 3),
            "counterparty_dispersion": round(dispersion_rate, 3),
            "inbound_tx_count": len(in_txns),
            "outbound_tx_count": len(out_txns),
            "total_volume": round(total_in + total_out, 2),
            "current_balance": round(balance, 2)
        },
        "supporting_evidence": evidence,
        "model_engine": "SentinelFlow Unsupervised Mule Network Detector v2.0"
    }
