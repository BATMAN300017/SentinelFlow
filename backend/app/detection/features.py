import sqlite3
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

def extract_transaction_features(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derives genuine operational features from historical transactions prior to prediction time.
    NEVER accesses ground-truth labels.
    """
    source_acc = str(txn.get("source_account_id") or "")
    dest_acc = str(txn.get("destination_account_id") or "")
    device_id = txn.get("device_id")
    txn_amount = float(txn.get("amount") or 0.0)
    
    cursor = conn.cursor()
    
    # 1. Historical account transactions (last 30 transactions, ordered by created_at DESC)
    cursor.execute("""
        SELECT amount, created_at, destination_account_id, beneficiary_name, device_id, status, transaction_type
        FROM transactions
        WHERE source_account_id = ? AND id != ?
        ORDER BY created_at DESC LIMIT 50
    """, (source_acc, txn.get("id", "")))
    history = [dict(r._dict if hasattr(r, "_dict") else r) for r in cursor.fetchall()]
    
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
        d_acc = dict(acc_row._dict if hasattr(acc_row, "_dict") else acc_row)
        is_dormant_flag = 1 if d_acc.get("is_dormant") else 0
        acc_balance = float(d_acc.get("balance") or 0.0)
    else:
        is_dormant_flag = 0
        acc_balance = 0.0
        
    # Inbound vs Outbound totals for account
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0), COUNT(*)
        FROM transactions
        WHERE destination_account_id = ?
        LIMIT 100
    """, (source_acc,))
    in_row = cursor.fetchone()
    total_inbound = float(in_row[0]) if in_row else 0.0
    inbound_count = int(in_row[1]) if in_row else 0
    
    total_outbound = sum(amounts) + txn_amount
    outbound_count = history_count + 1
    
    in_out_ratio = round(total_inbound / (total_outbound + 1.0), 3)
    fan_in_ratio = round(inbound_count / (inbound_count + outbound_count + 1.0), 3)
    fan_out_ratio = round(outbound_count / (inbound_count + outbound_count + 1.0), 3)
    
    # Rapid movement of funds check (inbound followed by immediate outbound)
    rapid_movement = 0
    if total_inbound > 0 and txn_amount > 0:
        ratio = txn_amount / (total_inbound + 1.0)
        if 0.70 <= ratio <= 1.20:
            rapid_movement = 1
            
    # Velocity: count of transactions in last 10 minutes
    ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE source_account_id = ? AND created_at >= ? AND id != ?
    """, (source_acc, ten_mins_ago, txn.get("id", "")))
    short_vel_row = cursor.fetchone()
    short_window_count = int(short_vel_row[0]) + 1 if short_vel_row else 1
    short_window_sum = float(short_vel_row[1]) + txn_amount if short_vel_row else txn_amount
    
    # Structuring check (just below $10,000 USD or INR 200,000 threshold)
    structuring_flag = 0
    curr = str(txn.get("currency") or "USD").upper()
    if curr == "USD" and 9000 <= txn_amount < 10000:
        structuring_flag = 1
    elif curr == "INR" and 180000 <= txn_amount < 200000:
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
            
    return {
        "amount": txn_amount,
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
        "structuring_flag": structuring_flag,
        "round_amount_flag": round_amount_flag,
        "historical_amounts": amounts
    }
