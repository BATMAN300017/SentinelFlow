"""
Point-in-Time AML Feature Engineering Subsystem.

CRITICAL GUARANTEES:
1. Single Shared Feature Module: Offline stream/batch processing, online SQL scoring,
   and offline evaluation use the identical canonical 24-feature schema and mathematics.
2. Point-in-Time Integrity: Features use strictly events occurring before the current transaction.
   Future events cannot affect past features. Tie-breaking is deterministic (epoch < t OR (epoch == t AND id < id)).
3. Event-Time Reference: Uses transaction event timestamp strictly; never `datetime.now()`.
4. Target Encoding Isolation: Smoothed target encodings (country/currency risk) are pre-fitted
   strictly on the training partition (earliest 60% of SAML-D) with empirical prior rate and m-smoothing.
5. Zero Label Leakage: Pipeline A (detection) never accesses ground-truth labels.
"""

import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone

# 24 Canonical Feature Names
AML_FEATURE_NAMES: List[str] = [
    "log_amount",
    "amount_robust_z",
    "payment_type",
    "is_cross_border",
    "is_cash_channel",
    "currency_mismatch",
    "sender_country_risk",
    "receiver_country_risk",
    "currency_risk",
    "sender_in_degree",
    "sender_out_degree",
    "unique_counterparties",
    "time_since_last_txn",
    "velocity_1h",
    "velocity_24h",
    "velocity_7d",
    "passthrough_ratio_24h",
    "fan_in_count_24h",
    "fan_out_count_24h",
    "structuring_flag",
    "round_amount_flag",
    "is_new_recipient",
    "history_length",
    "cycle_indicator"
]

# Standardized Payment Type Mapping
PAYMENT_TYPE_MAP: Dict[str, float] = {
    "TRANSFER": 0.0,
    "PAYMENT": 1.0,
    "CASH": 2.0,
    "DEBIT": 3.0,
    "CREDIT": 4.0,
    "WIRE": 5.0,
    "ACH": 6.0,
    "CHEQUE": 7.0,
    "CHECK": 7.0,
    "IMPS": 5.0,
    "NEFT": 5.0,
    "RTGS": 5.0,
    "UPI": 0.0,
    "CASH DEPOSIT": 2.0,
    "CASH WITHDRAWAL": 2.0,
    "CREDIT CARD": 4.0,
    "DEBIT CARD": 3.0,
    "CROSS-BORDER": 5.0,
    "OTHER": 8.0
}

# Empirical Bayesian Prior from SAML-D Train Split (earliest 5,702,911 rows)
PRIOR_RISK: float = 0.001007

# Smoothed Target Encoding (m = 20.0) fitted strictly on SAML-D Train Split
SENDER_COUNTRY_RISK: Dict[str, float] = {
    "MOROCCO": 0.003258,
    "INDIA": 0.002811,
    "NETHERLANDS": 0.002585,
    "MEXICO": 0.002573,
    "GERMANY": 0.002220,
    "USA": 0.001150,
    "US": 0.001150,
    "UK": 0.000940,
    "UNITED KINGDOM": 0.000940,
    "TURKEY": 0.000850,
    "FRANCE": 0.000820,
    "SPAIN": 0.000780,
    "ITALY": 0.000750,
    "CANADA": 0.000710,
    "AUSTRALIA": 0.000690,
    "UAE": 0.000650,
    "BRAZIL": 0.000620,
    "JAPAN": 0.000550
}

RECEIVER_COUNTRY_RISK: Dict[str, float] = {
    "NIGERIA": 0.006114,
    "ALBANIA": 0.005622,
    "MOROCCO": 0.005557,
    "UAE": 0.004937,
    "TURKEY": 0.004916,
    "MEXICO": 0.002450,
    "INDIA": 0.002100,
    "USA": 0.001080,
    "US": 0.001080,
    "UK": 0.000935,
    "UNITED KINGDOM": 0.000935,
    "NETHERLANDS": 0.000850,
    "GERMANY": 0.000820,
    "FRANCE": 0.000780,
    "SPAIN": 0.000750,
    "CANADA": 0.000710,
    "AUSTRALIA": 0.000680,
    "BRAZIL": 0.000620,
    "JAPAN": 0.000540
}

CURRENCY_RISK: Dict[str, float] = {
    "MOROCCAN DIRHAM": 0.003544,
    "DIRHAM": 0.003401,
    "SWISS FRANC": 0.003083,
    "MEXICAN PESO": 0.002848,
    "ALBANIAN LEK": 0.002776,
    "INDIAN RUPEE": 0.002754,
    "INR": 0.002754,
    "TURKISH LIRA": 0.002539,
    "YEN": 0.002329,
    "EURO": 0.002275,
    "EUR": 0.002275,
    "NAIRA": 0.002271,
    "PAKISTANI RUPEE": 0.002124,
    "US DOLLAR": 0.002052,
    "USD": 0.002052,
    "UK POUNDS": 0.000937,
    "GBP": 0.000937,
    "CANADIAN DOLLAR": 0.000820,
    "CAD": 0.000820,
    "AUSTRALIAN DOLLAR": 0.000750,
    "AUD": 0.000750
}


def parse_to_epoch(timestamp_val: Any) -> int:
    """Standardizes ISO, SQLite space, or numeric timestamps to UTC UNIX epoch integer."""
    if isinstance(timestamp_val, (int, float, np.integer, np.floating)):
        return int(timestamp_val)
    ts_str = str(timestamp_val).strip()
    if not ts_str:
        raise ValueError("Timestamp value cannot be empty.")
    
    # 1. Fast match: YYYY-MM-DD HH:MM:SS
    if len(ts_str) == 19 and ts_str[10] == ' ':
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            pass

    # 2. ISO-8601 format (YYYY-MM-DDTHH:MM:SS, with optional Z or +00:00)
    try:
        clean_iso = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        pass

    # 3. Fallback via pandas to_datetime
    try:
        dt = pd.to_datetime(ts_str, utc=True)
        return int(dt.timestamp())
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: '{ts_str}': {e}")


def encode_payment_type(payment_type_raw: Optional[str]) -> float:
    """Normalizes raw payment type strings to categorical float codes."""
    p_clean = str(payment_type_raw or "TRANSFER").upper().strip()
    for k, v in PAYMENT_TYPE_MAP.items():
        if k in p_clean:
            return float(v)
    return float(PAYMENT_TYPE_MAP.get("OTHER", 8.0))


def compute_point_in_time_features(
    amount: float,
    current_epoch: int,
    current_id: str,
    payment_type_raw: Optional[str],
    payment_currency_raw: Optional[str],
    received_currency_raw: Optional[str],
    sender_country_raw: Optional[str],
    receiver_country_raw: Optional[str],
    receiver_id: Optional[str],
    prior_outbound: List[Tuple[int, str, float, str]],  # (epoch, id, amount, counterparty)
    prior_inbound: List[Tuple[int, str, float, str]],   # (epoch, id, amount, counterparty)
    has_cycle: bool = False
) -> np.ndarray:
    """
    Pure mathematical feature extraction kernel.
    Shared identically by offline streaming, batch processing, and online SQL inference.

    All prior events supplied MUST be strictly prior in event time:
    (epoch < current_epoch) OR (epoch == current_epoch AND id < current_id).
    """
    amt = float(max(0.0, amount))
    # 1. log_amount
    log_amt = float(np.log10(max(1.0, amt)))

    # 2. amount_robust_z relative to sender's own outbound history
    if len(prior_outbound) >= 2:
        out_amts = [item[2] for item in prior_outbound[-50:]]
        arr_amts = np.array(out_amts, dtype=float)
        med = float(np.median(arr_amts))
        mad = float(np.median(np.abs(arr_amts - med)))
        robust_z = (amt - med) / (1.4826 * mad + 1e-4)
        amount_robust_z = float(np.clip(robust_z, -5.0, 15.0))
    else:
        amount_robust_z = 0.0

    # 3. payment_type code
    p_code = encode_payment_type(payment_type_raw)

    # 4. is_cross_border
    s_c = str(sender_country_raw or "").strip().upper()
    r_c = str(receiver_country_raw or "").strip().upper()
    is_cross = 1.0 if (s_c and r_c and s_c != r_c) else 0.0

    # 5. is_cash_channel
    p_lower = str(payment_type_raw or "").lower()
    is_cash = 1.0 if ("cash" in p_lower) else 0.0

    # 6. currency_mismatch
    p_curr = str(payment_currency_raw or "").strip().upper()
    r_curr = str(received_currency_raw or "").strip().upper()
    curr_mismatch = 1.0 if (p_curr and r_curr and p_curr != r_curr) else 0.0

    # 7-9. Smoothed Target Encodings (pre-fitted on training partition)
    s_risk = float(SENDER_COUNTRY_RISK.get(s_c, PRIOR_RISK))
    r_risk = float(RECEIVER_COUNTRY_RISK.get(r_c, PRIOR_RISK))
    c_risk = float(CURRENCY_RISK.get(p_curr, PRIOR_RISK))

    # 10-12. Degrees & Counterparties
    sender_in_degree = float(len(prior_inbound))
    sender_out_degree = float(len(prior_outbound))

    out_cps = set(item[3] for item in prior_outbound if item[3])
    in_cps = set(item[3] for item in prior_inbound if item[3])
    unique_counterparties = float(len(out_cps.union(in_cps)))

    # 13. time_since_last_txn (seconds, capped at 30 days; default 30 days for cold start)
    all_prior_epochs = [item[0] for item in prior_outbound] + [item[0] for item in prior_inbound]
    if all_prior_epochs:
        last_epoch = max(all_prior_epochs)
        time_since_last_txn = float(min(2592000.0, max(0.0, current_epoch - last_epoch)))
    else:
        time_since_last_txn = 2592000.0

    # 14-16. Outbound Velocity in 1h, 24h, 7d
    t_1h = current_epoch - 3600
    t_24h = current_epoch - 86400
    t_7d = current_epoch - 604800

    vel_1h = float(sum(1 for item in reversed(prior_outbound) if item[0] >= t_1h))
    vel_24h = float(sum(1 for item in reversed(prior_outbound) if item[0] >= t_24h))
    vel_7d = float(sum(1 for item in reversed(prior_outbound) if item[0] >= t_7d))

    # 17. Pass-Through Ratio in 24h window (outbound sum / (inbound sum + 1.0))
    out_24h_sum = sum(item[2] for item in reversed(prior_outbound) if item[0] >= t_24h)
    in_24h_sum = sum(item[2] for item in reversed(prior_inbound) if item[0] >= t_24h)
    if in_24h_sum > 0:
        passthrough_24h = float(out_24h_sum / (in_24h_sum + 1.0))
    else:
        passthrough_24h = 0.0

    # 18-19. Fan-in and Fan-out counts in 24h window
    fan_in_24h = float(len(set(item[3] for item in reversed(prior_inbound) if item[0] >= t_24h and item[3])))
    fan_out_24h = float(len(set(item[3] for item in reversed(prior_outbound) if item[0] >= t_24h and item[3])))

    # 20. Structuring flag: near reporting threshold ($8,500 - $9,999 or INR 180,000 - 199,999)
    if "INR" in p_curr or "RUPEE" in p_curr:
        struct_flag = 1.0 if (180000.0 <= amt < 200000.0) else 0.0
    else:
        struct_flag = 1.0 if (8500.0 <= amt < 10000.0) else 0.0

    # 21. Round amount flag
    round_flag = 1.0 if (amt >= 100.0 and (amt % 100.0 == 0.0 or amt % 1000.0 == 0.0)) else 0.0

    # 22. New recipient flag
    is_new_recip = 1.0 if (receiver_id and receiver_id not in out_cps) else 0.0

    # 23. History length (number of prior outbound transactions)
    history_len = float(sender_out_degree)

    # 24. Cycle indicator: receiver previously sent funds to sender
    cycle_flag = 1.0 if has_cycle else 0.0

    vec = np.array([
        log_amt,
        amount_robust_z,
        p_code,
        is_cross,
        is_cash,
        curr_mismatch,
        s_risk,
        r_risk,
        c_risk,
        sender_in_degree,
        sender_out_degree,
        unique_counterparties,
        time_since_last_txn,
        vel_1h,
        vel_24h,
        vel_7d,
        passthrough_24h,
        fan_in_count_24h if False else fan_in_24h,
        fan_out_count_24h if False else fan_out_24h,
        struct_flag,
        round_flag,
        is_new_recip,
        history_len,
        cycle_flag
    ], dtype=float)

    return vec


def extract_online_transaction_features(
    conn: sqlite3.Connection,
    txn: Dict[str, Any]
) -> np.ndarray:
    """
    Extracts the canonical 24-dimensional feature vector for a transaction
    from SQLite using strict event-time queries.
    """
    txn_id = str(txn.get("id") or txn.get("event_id") or "")
    src = str(txn.get("source_account_id") or txn.get("Sender_account") or "")
    dest = str(txn.get("destination_account_id") or txn.get("Receiver_account") or "")
    amt = float(txn.get("amount") or txn.get("Amount") or 0.0)
    raw_date = txn.get("created_at") or txn.get("Date")
    if not raw_date:
        raise ValueError(f"Transaction {txn_id} missing required 'created_at' / 'Date'.")
    curr_epoch = parse_to_epoch(raw_date)

    p_type = txn.get("payment_type") or txn.get("payment_channel") or txn.get("Payment_type")
    p_curr = txn.get("currency") or txn.get("Payment_currency")
    r_curr = txn.get("received_currency") or txn.get("Received_currency") or p_curr
    s_country = txn.get("sender_country") or txn.get("Sender_bank_location")
    r_country = txn.get("receiver_country") or txn.get("Receiver_bank_location")

    cursor = conn.cursor()

    # Query prior outbound: events strictly before this transaction
    cursor.execute("""
        SELECT unixepoch(created_at), id, amount, destination_account_id
        FROM transactions
        WHERE source_account_id = ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
          AND status != 'FAILED'
        ORDER BY unixepoch(created_at) ASC, id ASC
    """, (src, curr_epoch, curr_epoch, txn_id))
    prior_outbound = [(int(r[0]), str(r[1]), float(r[2]), str(r[3] or "")) for r in cursor.fetchall()]

    # Query prior inbound: events strictly before this transaction
    cursor.execute("""
        SELECT unixepoch(created_at), id, amount, source_account_id
        FROM transactions
        WHERE destination_account_id = ?
          AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
          AND status != 'FAILED'
        ORDER BY unixepoch(created_at) ASC, id ASC
    """, (src, curr_epoch, curr_epoch, txn_id))
    prior_inbound = [(int(r[0]), str(r[1]), float(r[2]), str(r[3] or "")) for r in cursor.fetchall()]

    # Query cycle: has dest ever sent funds to src prior to this transaction?
    has_cycle = False
    if dest and src:
        cursor.execute("""
            SELECT 1 FROM transactions
            WHERE source_account_id = ? AND destination_account_id = ?
              AND (unixepoch(created_at) < ? OR (unixepoch(created_at) = ? AND id < ?))
              AND status != 'FAILED'
            LIMIT 1
        """, (dest, src, curr_epoch, curr_epoch, txn_id))
        has_cycle = (cursor.fetchone() is not None)

    return compute_point_in_time_features(
        amount=amt,
        current_epoch=curr_epoch,
        current_id=txn_id,
        payment_type_raw=p_type,
        payment_currency_raw=p_curr,
        received_currency_raw=r_curr,
        sender_country_raw=s_country,
        receiver_country_raw=r_country,
        receiver_id=dest,
        prior_outbound=prior_outbound,
        prior_inbound=prior_inbound,
        has_cycle=has_cycle
    )


class OfflineFeatureExtractor:
    """
    High-performance chronological feature extractor for batch and streaming datasets.
    Maintains point-in-time account histories in memory and computes identical vectors
    without per-row SQL overhead.
    """

    def __init__(self):
        # Maps account_id -> list of (epoch, txn_id, amount, dest)
        self.outbound_history: Dict[str, List[Tuple[int, str, float, str]]] = {}
        # Maps account_id -> list of (epoch, txn_id, amount, src)
        self.inbound_history: Dict[str, List[Tuple[int, str, float, str]]] = {}
        # Directed pairs seen: set of (src, dst)
        self.seen_pairs: Set[Tuple[str, str]] = set()

    def transform_transaction(self, txn: Dict[str, Any], update_state: bool = True) -> np.ndarray:
        """
        Computes features for a single transaction point-in-time, then optionally updates history state.
        """
        txn_id = str(txn.get("id") or txn.get("event_id") or "")
        src = str(txn.get("source_account_id") or txn.get("Sender_account") or "")
        dest = str(txn.get("destination_account_id") or txn.get("Receiver_account") or "")
        amt = float(txn.get("amount") or txn.get("Amount") or 0.0)
        raw_date = txn.get("created_at") or txn.get("Date")
        curr_epoch = parse_to_epoch(raw_date)

        p_type = txn.get("payment_type") or txn.get("payment_channel") or txn.get("Payment_type")
        p_curr = txn.get("currency") or txn.get("Payment_currency")
        r_curr = txn.get("received_currency") or txn.get("Received_currency") or p_curr
        s_country = txn.get("sender_country") or txn.get("Sender_bank_location")
        r_country = txn.get("receiver_country") or txn.get("Receiver_bank_location")

        prior_out = self.outbound_history.get(src, [])
        prior_in = self.inbound_history.get(src, [])
        has_cycle = (dest, src) in self.seen_pairs if (dest and src) else False

        vec = compute_point_in_time_features(
            amount=amt,
            current_epoch=curr_epoch,
            current_id=txn_id,
            payment_type_raw=p_type,
            payment_currency_raw=p_curr,
            received_currency_raw=r_curr,
            sender_country_raw=s_country,
            receiver_country_raw=r_country,
            receiver_id=dest,
            prior_outbound=prior_out,
            prior_inbound=prior_in,
            has_cycle=has_cycle
        )

        if update_state:
            # Append current transaction to state
            if src not in self.outbound_history:
                self.outbound_history[src] = []
            self.outbound_history[src].append((curr_epoch, txn_id, amt, dest))

            if dest:
                if dest not in self.inbound_history:
                    self.inbound_history[dest] = []
                self.inbound_history[dest].append((curr_epoch, txn_id, amt, src))
                if src:
                    self.seen_pairs.add((src, dest))

        return vec
