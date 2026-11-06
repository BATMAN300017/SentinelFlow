import sqlite3
from typing import Dict, Any, List
import numpy as np
from datetime import datetime
import pandas as pd

def _row_to_dict(row, col_names: List[str]) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return {col: val for col, val in zip(col_names, row)}

def _parse_ts(ts: Any):
    if not ts:
        return None
    try:
        s = str(ts).replace("Z", "+00:00").strip()
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return pd.to_datetime(ts).to_pydatetime()
        except Exception:
            return None

def analyze_suspicious_account_network(conn: sqlite3.Connection, account_id: str) -> Dict[str, Any]:
    """
    Distinct Analytical Output: Suspicious Account / Network Prediction.
    Evaluates linked transactions, counterparty network, and fund pass-through behavior
    to independently predict whether an account operates as a Money Mule.
    NEVER accesses ground-truth labels.
    """
    if conn is None or not account_id:
        return {
            "account_id": account_id,
            "status": "UNAVAILABLE",
            "predicted_mule_probability": None,
            "mule_risk_tier": "UNAVAILABLE",
            "network_role": "UNKNOWN",
            "role_description": "Account mule prediction is unavailable (missing connection or account ID).",
            "signals": {},
            "supporting_evidence": [],
            "model_engine": "SentinelFlow Mule Network Detector v3.0 (Calibrated)"
        }

    cursor = conn.cursor()
    
    # 1. Query outbound transactions (capped at 100 for bounded execution)
    cursor.execute("""
        SELECT id, amount, destination_account_id, payment_channel, transaction_type, created_at
        FROM transactions
        WHERE source_account_id = ?
        ORDER BY created_at DESC LIMIT 100
    """, (account_id,))
    out_cols = ["id", "amount", "destination_account_id", "payment_channel", "transaction_type", "created_at"]
    out_rows = cursor.fetchall()
    
    # 2. Query inbound transactions (capped at 100)
    cursor.execute("""
        SELECT id, amount, source_account_id, payment_channel, transaction_type, created_at
        FROM transactions
        WHERE destination_account_id = ?
        ORDER BY created_at DESC LIMIT 100
    """, (account_id,))
    in_cols = ["id", "amount", "source_account_id", "payment_channel", "transaction_type", "created_at"]
    in_rows = cursor.fetchall()
    
    out_txns = [_row_to_dict(r, out_cols) for r in out_rows]
    in_txns = [_row_to_dict(r, in_cols) for r in in_rows]
    
    total_out = sum(float(t.get("amount") or 0.0) for t in out_txns)
    total_in = sum(float(t.get("amount") or 0.0) for t in in_txns)
    total_txns = len(out_txns) + len(in_txns)
    total_volume = total_in + total_out

    # Check account status from accounts table
    cursor.execute("SELECT balance, is_dormant, currency, created_at FROM accounts WHERE id = ?", (account_id,))
    acc_row = cursor.fetchone()
    if acc_row:
        acc_dict = _row_to_dict(acc_row, ["balance", "is_dormant", "currency", "created_at"])
        is_dormant = bool(acc_dict.get("is_dormant", False))
        balance = float(acc_dict.get("balance") or 0.0)
        curr = str(acc_dict.get("currency") or "INR").upper()
    else:
        is_dormant = False
        balance = 0.0
        curr = "INR"

    # If account has zero transaction history, fail closed with INSUFFICIENT_DATA
    if total_txns == 0:
        return {
            "account_id": account_id,
            "status": "INSUFFICIENT_DATA",
            "predicted_mule_probability": None,
            "mule_risk_tier": "UNAVAILABLE",
            "network_role": "INSUFFICIENT_DATA",
            "role_description": "No transaction history exists to evaluate account network behavior.",
            "signals": {
                "inbound_tx_count": 0,
                "outbound_tx_count": 0,
                "total_volume": 0.0,
                "current_balance": balance
            },
            "supporting_evidence": ["Zero historical transactions associated with account."],
            "model_engine": "SentinelFlow Mule Network Detector v3.0 (Calibrated)"
        }

    out_counterparties = set(t.get("destination_account_id") for t in out_txns if t.get("destination_account_id"))
    in_counterparties = set(t.get("source_account_id") for t in in_txns if t.get("source_account_id"))
    total_unique_cps = len(out_counterparties.union(in_counterparties))
    dispersion_rate = total_unique_cps / (total_txns + 1.0)

    # Operational amounts
    all_amounts = [float(t.get("amount") or 0.0) for t in out_txns + in_txns]
    max_amount = max(all_amounts) if all_amounts else 0.0
    avg_amount = total_volume / max(1, total_txns)

    # 3. Calculate Operational Mule Signals
    if total_in > 0 and total_out > 0:
        pass_through_ratio = min(total_in, total_out) / (max(total_in, total_out) + 1.0)
    else:
        pass_through_ratio = 0.0

    # Structural Signals (Staging, Collection Funnel, Disbursal Hub, Offshore Node)
    # Collection Funnel: multi-source fan-in or high single-source entry inflow
    if len(in_counterparties) >= 4:
        s_collection = 0.85 if total_in >= 50000.0 else 0.50
    elif len(in_counterparties) >= 2 and total_in >= 50000.0:
        s_collection = 0.70
    elif len(in_counterparties) >= 1 and (total_in >= 50000.0 or max_amount >= 50000.0):
        s_collection = 0.65 if len(out_counterparties) <= 1 else 0.50
    else:
        s_collection = 0.0

    # Disbursal Hub: fan-out to multiple off-ramps
    if len(out_counterparties) >= 4 and total_out >= 50000.0:
        s_disbursal = 0.85
    elif len(out_counterparties) >= 2 and total_out >= 50000.0:
        s_disbursal = 0.65
    elif len(out_counterparties) >= 1 and (total_out >= 50000.0 or max_amount >= 50000.0):
        s_disbursal = 0.50
    else:
        s_disbursal = 0.0

    # Staging signal: high pass-through with rapid forwarding
    if pass_through_ratio >= 0.50 and total_volume >= 25000.0:
        s_staging = min(1.0, pass_through_ratio * 1.1)
    elif pass_through_ratio >= 0.30 and total_volume >= 20000.0:
        s_staging = min(1.0, pass_through_ratio * 0.9)
    else:
        s_staging = pass_through_ratio * 0.50

    # Offshore hub / high-value cross-border single hop
    s_offshore = 0.85 if (curr in ["AED", "USD", "GBP", "EUR"] or "UAE" in account_id or "UK" in account_id) and max_amount >= 50000.0 else 0.0

    s_structural = max(s_staging, s_collection, s_disbursal, s_offshore)

    # Burst rate / temporal concentration
    all_ts = [_parse_ts(t.get("created_at")) for t in out_txns + in_txns]
    valid_ts = [t for t in all_ts if t is not None]
    if len(valid_ts) >= 2:
        span_hours = max(0.5, (max(valid_ts) - min(valid_ts)).total_seconds() / 3600.0)
        tx_per_day = (total_txns / span_hours) * 24.0
        s_burst = min(1.0, tx_per_day / 6.0)
    else:
        s_burst = 0.60

    # Volume signal
    s_volume = min(1.0, total_volume / 250000.0)
    if max_amount >= 100000.0:
        s_volume = max(s_volume, 0.85)

    s_dormant = 0.80 if (is_dormant and total_txns > 3) else 0.0

    # 4. Benign Exclusion / Lookalike Validation
    salary_vol = sum(float(t.get("amount") or 0.0) for t in out_txns if str(t.get("transaction_type", "")).upper() == "SALARY")
    salary_cnt = sum(1 for t in out_txns if str(t.get("transaction_type", "")).upper() == "SALARY")
    is_payroll = (salary_cnt >= 5 and salary_vol >= 0.50 * max(1.0, total_out))

    # Low-value domestic retail merchant or standard consumer micro-transactions
    is_micro_retail = (max_amount < 15000.0 and total_volume < 100000.0 and avg_amount < 5000.0 and pass_through_ratio < 0.25)

    # 5. Composite Probability Calculation
    raw_mule_score = (
        0.40 * s_structural +
        0.25 * s_burst +
        0.20 * s_volume +
        0.15 * min(1.0, total_unique_cps / 8.0)
    )
    if s_dormant > 0:
        raw_mule_score = min(1.0, raw_mule_score + 0.10)

    if is_payroll:
        raw_mule_score *= 0.30  # Strongly discount corporate payroll
    elif is_micro_retail:
        raw_mule_score *= 0.30  # Strongly discount micro-merchant retail aggregation

    calibrated_prob = round(float(1.0 / (1.0 + np.exp(-6.5 * (raw_mule_score - 0.45)))), 4)

    # 6. Classify Network Role
    if is_payroll:
        network_role = "LEGITIMATE_CORPORATE_PAYROLL"
        role_desc = "Verified corporate entity executing bulk employee salary disbursements."
    elif is_micro_retail:
        network_role = "LEGITIMATE_RETAIL_COMMERCE"
        role_desc = "Low-value domestic retail merchant or standard consumer micro-transactions."
    elif len(in_counterparties) >= 4 and len(out_counterparties) <= 2:
        network_role = "MULE_COLLECTION_FUNNEL"
        role_desc = f"Account funnels funds from {len(in_counterparties)} inbound sources into limited consolidation targets."
    elif len(out_counterparties) >= 4 and total_out > total_in * 1.5:
        network_role = "MULE_DISBURSAL_HUB"
        role_desc = f"Account rapidly disperses liquidity across {len(out_counterparties)} distinct counterparty nodes."
    elif pass_through_ratio >= 0.60 and total_txns >= 4:
        network_role = "MULE_STAGING_ACCOUNT"
        role_desc = f"High pass-through velocity ({pass_through_ratio*100:.1f}%) observed; funds forwarded rapidly."
    elif calibrated_prob >= 0.70:
        network_role = "HIGH_RISK_SYNDICATE_NODE"
        role_desc = "Multi-signal structural anomaly in transaction timing and counterparty concentration."
    else:
        network_role = "STANDARD_OPERATING_ACCOUNT"
        role_desc = "Account behavior conforms to routine operational parameters."

    # Evidence items supporting account-level prediction
    evidence = [
        f"Total examined transactions: {total_txns} ({len(in_txns)} inbound, {len(out_txns)} outbound)",
        f"Total unique counterparties: {total_unique_cps} ({len(in_counterparties)} sources, {len(out_counterparties)} destinations)",
        f"Cumulative volume: {curr} {total_volume:,.2f} (In: {total_in:,.2f}, Out: {total_out:,.2f})",
        f"Liquidity pass-through ratio: {pass_through_ratio * 100:.1f}%, structural signal: {s_structural:.2f}",
        f"Operational network role: {network_role}"
    ]
    if is_dormant:
        evidence.append("Account flagged as dormant prior to sudden velocity spike")

    mule_tier = (
        "CRITICAL" if calibrated_prob >= 0.80
        else "HIGH" if calibrated_prob >= 0.65
        else "MEDIUM" if calibrated_prob >= 0.45
        else "LOW"
    )

    return {
        "account_id": account_id,
        "status": "ACTIVE",
        "predicted_mule_probability": calibrated_prob,
        "mule_risk_tier": mule_tier,
        "network_role": network_role,
        "role_description": role_desc,
        "signals": {
            "pass_through_ratio": round(pass_through_ratio, 3),
            "counterparty_dispersion": round(dispersion_rate, 3),
            "inbound_tx_count": len(in_txns),
            "outbound_tx_count": len(out_txns),
            "total_volume": round(total_volume, 2),
            "max_amount": round(max_amount, 2),
            "avg_amount": round(avg_amount, 2),
            "current_balance": round(balance, 2),
            "structural_signal": round(s_structural, 3),
            "burst_signal": round(s_burst, 3)
        },
        "supporting_evidence": evidence,
        "model_engine": "SentinelFlow Mule Network Detector v3.0 (Calibrated)"
    }
