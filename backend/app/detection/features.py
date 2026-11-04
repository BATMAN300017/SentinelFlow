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
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta

# Single canonical 9-feature schema shared identically across training, inference and evaluation
CANONICAL_FEATURE_NAMES: List[str] = [
    "log_amount",             # float: log10(max(1.0, amount))
    "velocity_10m",           # float: number of outbound txns in prior 10m window (including current: >= 1.0)
    "rapid_movement",         # float: 1.0 if recent inbound (<30m) followed by outbound of comparable amount (0.7-1.25), else 0.0
    "structuring_flag",       # float: 1.0 if amount near reporting threshold ($8500-$9999 or INR 180k-199.9k), else 0.0
    "is_cross_border",        # float: 1.0 if sender country != receiver country, else 0.0
    "is_cash_channel",        # float: 1.0 if payment channel / type is cash, else 0.0
    "is_new_recipient",       # float: 1.0 if receiver was never seen in sender's prior history, else 0.0
    "past_recipient_count",   # float: count of distinct prior recipients seen from this sender (>= 0.0)
    "history_length"          # float: total prior outbound transactions from this sender (>= 0.0)
]

def validate_feature_vector(vec: np.ndarray) -> np.ndarray:
    """
    Validates that a feature vector matches the canonical 9-feature schema:
    - Dimensions: (*, 9)
    - All elements finite numeric floats (no NaN, null, or Inf)
    - Values within mathematical/operational bounds
    """
    if not isinstance(vec, np.ndarray):
        raise TypeError(f"Expected numpy.ndarray, got {type(vec).__name__}")
    if vec.ndim == 1:
        vec = vec.reshape(1, -1)
    if vec.shape[-1] != len(CANONICAL_FEATURE_NAMES):
        raise ValueError(
            f"Feature dimension mismatch: expected {len(CANONICAL_FEATURE_NAMES)} features, "
            f"got vector with shape {vec.shape}"
        )
    if not np.all(np.isfinite(vec)):
        raise ValueError("Feature vector contains non-finite (NaN, Inf, or None) values.")
    if np.any(vec[:, 0] < 0.0):
        raise ValueError(f"log_amount cannot be negative: min={np.min(vec[:, 0])}")
    if np.any(vec[:, 1] < 1.0):
        raise ValueError(f"velocity_10m must be >= 1.0 (including current transaction): min={np.min(vec[:, 1])}")
    for col_idx, col_name in [(2, "rapid_movement"), (3, "structuring_flag"), (4, "is_cross_border"), (5, "is_cash_channel"), (6, "is_new_recipient")]:
        invalid_mask = ~np.isin(vec[:, col_idx], [0.0, 1.0])
        if np.any(invalid_mask):
            raise ValueError(f"Binary feature '{col_name}' contains non-binary values: {vec[invalid_mask, col_idx]}")
    if np.any(vec[:, 7] < 0.0):
        raise ValueError(f"past_recipient_count cannot be negative: min={np.min(vec[:, 7])}")
    if np.any(vec[:, 8] < 0.0):
        raise ValueError(f"history_length cannot be negative: min={np.min(vec[:, 8])}")
    return vec


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
        "unique_counterparties": unique_counterparties,
        "past_recipient_count": float(unique_counterparties),
        "history_length": float(history_count),
        "is_new_beneficiary": is_new_beneficiary,
        "is_new_recipient": float(is_new_beneficiary),
        "shared_device_accounts": shared_device_accounts,
        "rapid_movement_detected": rapid_movement,
        "rapid_movement": float(rapid_movement),
        "velocity_10m": float(short_window_count),
        "recent_inbound_sum": recent_inbound_sum,
        "recent_inbound_count": recent_inbound_count,
        "structuring_flag": float(structuring_flag),
        "round_amount_flag": round_amount_flag,
        "is_cross_border": float(is_cross_border),
        "is_cash_channel": float(is_cash_channel),
        "historical_amounts": amounts
    }


def compute_samld_stream_features(
    df_or_records: Any,
    validate: bool = True
) -> Tuple[np.ndarray, List[str], pd.DataFrame]:
    """
    Shared, deterministic event-time feature-building implementation for SAML-D.
    Used identically for offline training, validation, holdout test evaluation,
    and batch streaming.

    Guarantees:
    - Same canonical 9-feature schema and ordering as online inference.
    - Deterministic tie-breaking on same-timestamp records via stable transaction ID.
    - Zero self-leakage and zero look-ahead bias: a transaction never uses its own
      features or future transactions as history.
    - Fails closed on missing timestamps or non-finite values (never substitutes datetime.now()).
    - Returns (X: ndarray of shape (N, 9), feature_names: List[str], df: DataFrame).
    """
    if isinstance(df_or_records, pd.DataFrame):
        df = df_or_records.copy()
    elif isinstance(df_or_records, list):
        df = pd.DataFrame(df_or_records)
    else:
        raise ValueError("df_or_records must be a pandas DataFrame or list of dicts.")

    # Validate required columns
    req_cols = ["Sender_account", "Receiver_account", "Amount"]
    for c in req_cols:
        if c not in df.columns:
            low_map = {col.lower(): col for col in df.columns}
            if c.lower() in low_map:
                df[c] = df[low_map[c.lower()]]
            else:
                raise ValueError(f"Missing required SAML-D column: '{c}'.")

    # Timestamp handling: require valid Date and Time or created_at
    if "Date" in df.columns and "Time" in df.columns:
        if df["Date"].isna().any() or df["Time"].isna().any():
            raise ValueError("Dataset contains null or missing Date/Time values.")
        date_str = df["Date"].astype(str).str.strip()
        time_str = df["Time"].astype(str).str.strip()
        if (date_str == "").any() or (time_str == "").any():
            raise ValueError("Dataset contains blank Date or Time values.")
        df["DateTime"] = pd.to_datetime(date_str + " " + time_str)
    elif "created_at" in df.columns:
        if df["created_at"].isna().any():
            raise ValueError("Dataset contains null or missing 'created_at' timestamps.")
        df["DateTime"] = pd.to_datetime(df["created_at"])
    else:
        raise ValueError("Dataset must contain either ('Date', 'Time') or 'created_at' timestamps.")

    if df["DateTime"].isna().any():
        raise ValueError("Failed to parse event timestamps into valid datetimes.")

    # Ensure stable transaction ID for deterministic tie-breaking
    if "id" in df.columns:
        df["txn_sort_id"] = df["id"].astype(str)
    elif "transaction_id" in df.columns:
        df["txn_sort_id"] = df["transaction_id"].astype(str)
    else:
        df["txn_sort_id"] = [f"SAML-D-{i:07d}" for i in range(len(df))]

    # Strict deterministic sort by (DateTime, txn_sort_id)
    df = df.sort_values(by=["DateTime", "txn_sort_id"], ascending=[True, True]).reset_index(drop=True)

    sender_out_history: Dict[str, List[Tuple[Any, float, str, str]]] = {}
    receiver_in_history: Dict[str, List[Tuple[Any, float, str, str]]] = {}
    feature_rows = []

    for idx, r in df.iterrows():
        sender = str(r["Sender_account"])
        receiver = str(r["Receiver_account"])
        amt = float(r["Amount"])
        if amt < 0.0 or not np.isfinite(amt):
            raise ValueError(f"Transaction at row {idx} has invalid amount: {amt}")

        dt = r["DateTime"]
        cur_tid = str(r["txn_sort_id"])

        curr = str(r.get("Payment_currency", r.get("currency", "USD"))).upper()
        p_type = str(r.get("Payment_type", r.get("payment_type", "TRANSFER"))).lower()
        src_loc = str(r.get("Sender_bank_location", r.get("sender_country", "")))
        dest_loc = str(r.get("Receiver_bank_location", r.get("receiver_country", "")))

        # 1. log_amount: log10(max(1.0, amt))
        log_amt = round(float(np.log10(max(1.0, amt))), 4)

        # Sender prior outbound history strictly prior: (t < dt) OR (t == dt AND tid < cur_tid)
        out_hist = sender_out_history.get(sender, [])
        prior_out = [
            item for item in out_hist
            if (item[0] < dt) or (item[0] == dt and item[3] < cur_tid)
        ]

        # 2. velocity_10m: prior outbound in last 10m + 1.0
        t_10m = dt - pd.Timedelta(minutes=10)
        vel_10m_prior = len([
            item for item in prior_out
            if item[0] >= t_10m
        ])
        vel_10m = float(vel_10m_prior + 1.0)

        # 3. rapid_movement: recent inbound to sender within 30m followed by comparable outbound (0.70-1.25)
        in_hist = receiver_in_history.get(sender, [])
        t_30m = dt - pd.Timedelta(minutes=30)
        recent_in = [
            item[1] for item in in_hist
            if item[0] >= t_30m and ((item[0] < dt) or (item[0] == dt and item[3] < cur_tid))
        ]
        rapid_movement = 0.0
        if recent_in and amt > 0.0:
            for in_a in recent_in:
                if 0.70 <= (amt / (in_a + 1.0)) <= 1.25:
                    rapid_movement = 1.0
                    break

        # 4. structuring_flag: near reporting threshold
        is_struct = 1.0 if (
            (('POUND' in curr or 'USD' in curr or 'EUR' in curr) and (8500.0 <= amt < 10000.0)) or
            ('INR' in curr and (180000.0 <= amt < 200000.0)) or
            (8500.0 <= amt < 10000.0)
        ) else 0.0

        # 5. is_cross_border
        is_cross = 1.0 if (src_loc and dest_loc and src_loc != dest_loc) else 0.0

        # 6. is_cash_channel
        is_cash = 1.0 if "cash" in p_type else 0.0

        # 7. is_new_recipient & 8. past_recipient_count
        prior_recipients = set(item[2] for item in prior_out)
        is_new_recip = 1.0 if (receiver and receiver not in prior_recipients) else 0.0
        past_recip_count = float(len(prior_recipients))

        # 9. history_length
        hist_len = float(len(prior_out))

        row_vec = [log_amt, vel_10m, rapid_movement, is_struct, is_cross, is_cash, is_new_recip, past_recip_count, hist_len]
        feature_rows.append(row_vec)

        # Update event-time history with current transaction
        out_hist.append((dt, amt, receiver, cur_tid))
        sender_out_history[sender] = out_hist

        in_h = receiver_in_history.get(receiver, [])
        in_h.append((dt, amt, sender, cur_tid))
        receiver_in_history[receiver] = in_h

    X = np.array(feature_rows, dtype=float)

    if validate:
        validate_feature_vector(X)

    return X, CANONICAL_FEATURE_NAMES, df
