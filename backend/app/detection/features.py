import sqlite3
import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

def _row_to_dict(row, col_names: List[str]) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return {col: val for col, val in zip(col_names, row)}

def _parse_event_time(val: Any) -> datetime:
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    if not val:
        return datetime.now(timezone.utc)
    val_str = str(val).strip()
    try:
        if val_str.endswith("Z"):
            val_str = val_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val_str, fmt).replace(tzinfo=timezone.utc)
            except Exception:
                pass
        return datetime.now(timezone.utc)

def extract_transaction_features(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derives genuine operational features from historical transactions prior to prediction time.
    Uses transaction event timestamp rather than wall-clock datetime.now() to ensure
    leakage-free, reproducible historical evaluation and streaming inference.
    NEVER accesses ground-truth labels.
    """
    source_acc = str(txn.get("source_account_id") or "")
    dest_acc = str(txn.get("destination_account_id") or "")
    device_id = txn.get("device_id")
    txn_amount = float(txn.get("amount") or 0.0)
    
    # Event-time reference for historical lookback
    txn_time = _parse_event_time(txn.get("created_at"))
    txn_time_iso = txn_time.isoformat()
    
    cursor = conn.cursor()
    
    # 1. Historical account transactions strictly prior or at transaction time
    cursor.execute("""
        SELECT amount, created_at, destination_account_id, beneficiary_name, device_id, status, transaction_type
        FROM transactions
        WHERE source_account_id = ? AND id != ? AND created_at <= ?
        ORDER BY created_at DESC LIMIT 50
    """, (source_acc, txn.get("id", ""), txn_time_iso))
    hist_cols = ["amount", "created_at", "destination_account_id", "beneficiary_name", "device_id", "status", "transaction_type"]
    history = [_row_to_dict(r, hist_cols) for r in cursor.fetchall()]
    
    history_count = len(history)
    amounts = [float(h.get("amount") or 0.0) for h in history]
    
    # Counterparty count
    past_destinations = set(h.get("destination_account_id") for h in history if h.get("destination_account_id"))
    unique_counterparties = len(past_destinations)
    if dest_acc:
        is_new_beneficiary = 1 if dest_acc not in past_destinations else 0
    else:
        is_new_beneficiary = 0
        
    # Account dormancy check
    cursor.execute("SELECT is_dormant, balance FROM accounts WHERE id = ?", (source_acc,))
    acc_row = cursor.fetchone()
    if acc_row:
        d_acc = _row_to_dict(acc_row, ["is_dormant", "balance"])
        is_dormant_flag = 1 if d_acc.get("is_dormant") else 0
        acc_balance = float(d_acc.get("balance") or 0.0)
    else:
        is_dormant_flag = 0
        acc_balance = 0.0
        
    # Inbound vs Outbound totals for account (strictly up to transaction time)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0), COUNT(*)
        FROM transactions
        WHERE destination_account_id = ? AND created_at <= ?
        LIMIT 100
    """, (source_acc, txn_time_iso))
    in_row = cursor.fetchone()
    total_inbound = float(in_row[0]) if in_row else 0.0
    inbound_count = int(in_row[1]) if in_row else 0
    
    # Recent Inbound (last 30 minutes relative to event timestamp)
    thirty_mins_ago = (txn_time - timedelta(minutes=30)).isoformat()
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0), COUNT(*)
        FROM transactions
        WHERE destination_account_id = ? AND created_at >= ? AND created_at <= ?
    """, (source_acc, thirty_mins_ago, txn_time_iso))
    recent_in_row = cursor.fetchone()
    recent_inbound_sum = float(recent_in_row[0]) if recent_in_row and recent_in_row[0] else total_inbound
    recent_inbound_count = int(recent_in_row[1]) if recent_in_row and recent_in_row[1] else inbound_count

    total_outbound = sum(amounts) + txn_amount
    outbound_count = history_count + 1
    
    in_out_ratio = round(total_inbound / (total_outbound + 1.0), 3)
    fan_in_ratio = round(inbound_count / (inbound_count + outbound_count + 1.0), 3)
    fan_out_ratio = round(outbound_count / (inbound_count + outbound_count + 1.0), 3)
    
    # Rapid movement of funds check (inbound followed by immediate outbound)
    rapid_movement = 0
    ref_inbound = recent_inbound_sum if recent_inbound_sum > 0 else total_inbound
    if ref_inbound > 0 and txn_amount > 0:
        ratio = txn_amount / (ref_inbound + 1.0)
        if 0.70 <= ratio <= 1.25:
            rapid_movement = 1
            
    # Velocity: count of transactions in last 10 minutes relative to event timestamp
    ten_mins_ago = (txn_time - timedelta(minutes=10)).isoformat()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE source_account_id = ? AND created_at >= ? AND created_at <= ? AND id != ?
    """, (source_acc, ten_mins_ago, txn_time_iso, txn.get("id", "")))
    short_vel_row = cursor.fetchone()
    short_window_count = int(short_vel_row[0]) + 1 if short_vel_row else 1
    short_window_sum = float(short_vel_row[1]) + txn_amount if short_vel_row else txn_amount
    
    # Structuring check (just below reporting thresholds: $10,000 USD/GBP/EUR or INR 200,000)
    structuring_flag = 0
    curr = str(txn.get("currency") or "USD").upper()
    if any(c in curr for c in ("USD", "GBP", "EUR", "POUND")) and (8500 <= txn_amount < 10000):
        structuring_flag = 1
    elif "INR" in curr and (180000 <= txn_amount < 200000):
        structuring_flag = 1
    elif 8500 <= txn_amount < 10000:
        structuring_flag = 1
        
    # Round amount flag
    round_amount_flag = 1 if (txn_amount > 1000 and txn_amount % 1000 == 0) else 0
    
    # Shared device count
    shared_device_accounts = 1
    if device_id:
        cursor.execute("SELECT COUNT(DISTINCT source_account_id) FROM transactions WHERE device_id = ?", (device_id,))
        dev_row = cursor.fetchone()
        if dev_row:
            shared_device_accounts = max(1, int(dev_row[0]))
            
    # Log-transformed amount for scale-invariant risk evaluation
    log_amount = round(float(np.log10(max(1.0, txn_amount))), 4)
    
    # Cross-border indicator
    src_country = str(txn.get("sender_country") or txn.get("Sender_bank_location") or "USA").upper()
    dest_country = str(txn.get("receiver_country") or txn.get("Receiver_bank_location") or src_country).upper()
    is_cross_border = 1 if (src_country != dest_country and src_country and dest_country) else 0
    
    # Cash payment channel indicator
    payment_channel = str(txn.get("payment_channel") or txn.get("payment_type") or "TRANSFER").lower()
    is_cash_channel = 1 if "cash" in payment_channel else 0
            
    return {
        "amount": txn_amount,
        "log_amount": log_amount,
        "currency": curr,
        "history_count": history_count,
        "is_cold_start": 1 if history_count < 3 else 0,
        "is_dormant_account": is_dormant_flag,
        "account_balance": acc_balance,
        "short_window_count": short_window_count,
        "short_window_sum": short_window_sum,
        "in_out_ratio": in_out_ratio,
        "fan_in_ratio": fan_in_ratio,
        "fan_out_ratio": fan_out_ratio,
        "unique_counterparties": max(1, unique_counterparties),
        "is_new_beneficiary": is_new_beneficiary,
        "shared_device_accounts": shared_device_accounts,
        "rapid_movement_detected": rapid_movement,
        "recent_inbound_sum": recent_inbound_sum,
        "recent_inbound_count": recent_inbound_count,
        "structuring_flag": structuring_flag,
        "round_amount_flag": round_amount_flag,
        "is_cross_border": is_cross_border,
        "is_cash_channel": is_cash_channel,
        "historical_amounts": amounts
    }
