"""
Event-Time Operational Feature Extraction Subsystem.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. Strict Event-Time Reference: All historical aggregates, windows, and graph signals
   must use transactions strictly earlier than the transaction being scored.
2. Deterministic Tie-Breaking: If transactions share the exact same timestamp,
   ties are broken deterministically using transaction ID:
   (unixepoch(created_at) < txn_epoch) OR (unixepoch(created_at) == txn_epoch AND id < txn_id)
3. Exclude Self: The transaction being scored is strictly excluded from all historical aggregates.
4. Point-in-Time Integrity: Mutable current account balances or current account statuses
   are NOT used as historical features unless a valid point-in-time calculation exists.
5. Consistent Epoch Timestamp Evaluation: SQLite unixepoch(created_at) standardizes across
   any string format (ISO-8601 with Z, +00:00, or spaces).
6. Zero Label Access: NEVER accesses fraud, mule, or laundering ground-truth labels.
"""

import sqlite3
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

def _row_to_dict(row, col_names: List[str]) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return {col: val for col, val in zip(col_names, row)}

def parse_event_time(val: Any) -> datetime:
    """
    Parses and standardizes an event timestamp to a UTC-aware datetime.
    STRICT: Requires a valid event timestamp for historical evaluation;
    never silently substitutes datetime.now().
    """
    if val is None or val == "":
        raise ValueError("Missing required transaction event timestamp ('created_at' cannot be empty).")
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    
    val_str = str(val).strip()
    if not val_str:
        raise ValueError("Missing required transaction event timestamp ('created_at' is blank).")
    
    # Handle ISO formats
    try:
        clean_str = val_str
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d"
    ):
        try:
            return datetime.strptime(val_str, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    raise ValueError(f"Invalid or unparseable event timestamp: '{val_str}'")

def extract_transaction_features(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derives genuine operational features strictly prior to the transaction event timestamp.
    Enforces deterministic ordering, point-in-time dormancy, and zero data leakage.
    """
    txn_id = str(txn.get("id") or "")
    source_acc = str(txn.get("source_account_id") or "")
    dest_acc = str(txn.get("destination_account_id") or "")
    device_id = txn.get("device_id")
    txn_amount = float(txn.get("amount") or 0.0)
    curr = str(txn.get("currency") or "USD").upper()

    # 1. Require valid event timestamp - do NOT silently replace with datetime.now()
    raw_created_at = txn.get("created_at")
    if not raw_created_at:
        raise ValueError(f"Transaction {txn_id} requires a valid 'created_at' timestamp for event-time scoring.")
    txn_time = parse_event_time(raw_created_at)
    txn_epoch = int(txn_time.timestamp())

    cursor = conn.cursor()

    # 2. Historical prior outbound transactions (strictly earlier: unixepoch < t OR (unixepoch == t AND id < id))
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE source_account_id = ?
          AND id != ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
    """, (source_acc, txn_id, txn_epoch, txn_epoch, txn_id))
    prior_out_stats = cursor.fetchone()
    history_count = int(prior_out_stats[0]) if prior_out_stats else 0
    total_prior_outbound_sum = float(prior_out_stats[1]) if prior_out_stats else 0.0

    # Retrieve recent prior amounts for MAD anomaly and counterparty analysis (up to 100)
    cursor.execute("""
        SELECT amount, destination_account_id
        FROM transactions
        WHERE source_account_id = ?
          AND id != ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
        ORDER BY unixepoch(created_at) DESC, id DESC
        LIMIT 100
    """, (source_acc, txn_id, txn_epoch, txn_epoch, txn_id))
    recent_prior_rows = cursor.fetchall()
    amounts = [float(r[0]) for r in recent_prior_rows]
    past_destinations = set(r[1] for r in recent_prior_rows if r[1])
    unique_counterparties = len(past_destinations)
    is_new_beneficiary = 1 if (dest_acc and dest_acc not in past_destinations) else 0

    # 3. Point-in-Time Account Dormancy:
    # Check the most recent transaction strictly prior to this event.
    # If inactive for >= 90 days and has prior history, mark as dormant at event time.
    cursor.execute("""
        SELECT created_at
        FROM transactions
        WHERE (source_account_id = ? OR destination_account_id = ?)
          AND id != ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
        ORDER BY unixepoch(created_at) DESC, id DESC
        LIMIT 1
    """, (source_acc, source_acc, txn_id, txn_epoch, txn_epoch, txn_id))
    last_prior_txn_row = cursor.fetchone()
    if last_prior_txn_row and last_prior_txn_row[0]:
        try:
            last_prior_time = parse_event_time(last_prior_txn_row[0])
            days_inactive = (txn_time - last_prior_time).total_seconds() / 86400.0
            is_dormant_flag = 1 if (days_inactive >= 90.0 and history_count > 0) else 0
        except Exception:
            is_dormant_flag = 0
    else:
        is_dormant_flag = 0

    # 4. Inbound totals strictly prior to event timestamp
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE destination_account_id = ?
          AND id != ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
    """, (source_acc, txn_id, txn_epoch, txn_epoch, txn_id))
    in_row = cursor.fetchone()
    inbound_count = int(in_row[0]) if in_row else 0
    total_inbound = float(in_row[1]) if in_row else 0.0

    # 5. Recent Inbound window (prior 30 minutes relative to event timestamp)
    thirty_mins_ago_epoch = txn_epoch - 1800
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE destination_account_id = ?
          AND id != ?
          AND unixepoch(created_at) >= ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
    """, (source_acc, txn_id, thirty_mins_ago_epoch, txn_epoch, txn_epoch, txn_id))
    recent_in_row = cursor.fetchone()
    recent_inbound_count = int(recent_in_row[0]) if recent_in_row else 0
    recent_inbound_sum = float(recent_in_row[1]) if recent_in_row else 0.0

    # Point-in-time estimated account balance (inbound minus outbound strictly prior to event)
    point_in_time_balance = max(0.0, total_inbound - total_prior_outbound_sum)

    total_outbound = total_prior_outbound_sum + txn_amount
    outbound_count = history_count + 1

    in_out_ratio = round(total_inbound / (total_outbound + 1.0), 3)
    fan_in_ratio = round(inbound_count / (inbound_count + outbound_count + 1.0), 3)
    fan_out_ratio = round(outbound_count / (inbound_count + outbound_count + 1.0), 3)

    # Rapid movement of funds check (recent inbound followed by immediate outbound)
    rapid_movement = 0
    ref_inbound = recent_inbound_sum if recent_inbound_sum > 0 else total_inbound
    if ref_inbound > 0 and txn_amount > 0:
        ratio = txn_amount / (ref_inbound + 1.0)
        if 0.70 <= ratio <= 1.25:
            rapid_movement = 1

    # 6. Rolling velocity window (prior 10 minutes relative to event timestamp)
    ten_mins_ago_epoch = txn_epoch - 600
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE source_account_id = ?
          AND id != ?
          AND unixepoch(created_at) >= ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
    """, (source_acc, txn_id, ten_mins_ago_epoch, txn_epoch, txn_epoch, txn_id))
    short_vel_row = cursor.fetchone()
    prior_short_count = int(short_vel_row[0]) if short_vel_row else 0
    prior_short_sum = float(short_vel_row[1]) if short_vel_row else 0.0
    short_window_count = prior_short_count + 1
    short_window_sum = prior_short_sum + txn_amount

    # 7. Structuring check (just below reporting thresholds: $10,000 USD/GBP/EUR or INR 200,000)
    structuring_flag = 0
    if any(c in curr for c in ("USD", "GBP", "EUR", "POUND")) and (8500 <= txn_amount < 10000):
        structuring_flag = 1
    elif "INR" in curr and (180000 <= txn_amount < 200000):
        structuring_flag = 1
    elif 8500 <= txn_amount < 10000:
        structuring_flag = 1

    # Round amount flag
    round_amount_flag = 1 if (txn_amount > 1000 and txn_amount % 1000 == 0) else 0

    # 8. Shared device count strictly prior to event timestamp
    shared_device_accounts = 1
    if device_id:
        cursor.execute("""
            SELECT COUNT(DISTINCT source_account_id)
            FROM transactions
            WHERE device_id = ?
              AND id != ?
              AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
        """, (device_id, txn_id, txn_epoch, txn_epoch, txn_id))
        dev_row = cursor.fetchone()
        if dev_row and dev_row[0]:
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
        "account_balance": point_in_time_balance,
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
