import json
from app.utils.json_utils import safe_json_loads
import sqlite3
from typing import List, Dict, Any

DEFAULT_RULES = [
    {
        "id": "RULE-VEL-01",
        "rule_code": "HIGH_VELOCITY_TRANSFERS",
        "name": "Rapid Consecutive Transfers",
        "description": "More than 4 transactions executed from the same account within a 10-minute window",
        "category": "VELOCITY",
        "severity": "HIGH",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"max_count_10m": 4}),
        "lookback_window_minutes": 10,
        "version": 1
    },
    {
        "id": "RULE-FLOW-02",
        "rule_code": "RAPID_FUND_MOVEMENT",
        "name": "Rapid Inbound to Outbound Forwarding",
        "description": "Account received significant funds and immediately forwarded >80% within 30 minutes",
        "category": "NETWORK",
        "severity": "CRITICAL",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"min_inbound": 5000.0, "forwarding_ratio": 0.80}),
        "lookback_window_minutes": 30,
        "version": 1
    },
    {
        "id": "RULE-DORM-03",
        "rule_code": "DORMANT_ACCOUNT_REACTIVATION",
        "name": "Sudden High-Value Transfer on Dormant Account",
        "description": "High value transfer originating from an account inactive for >180 days",
        "category": "TEMPORAL",
        "severity": "HIGH",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"min_amount": 2000.0}),
        "lookback_window_minutes": 1440,
        "version": 1
    },
    {
        "id": "RULE-DEV-04",
        "rule_code": "SHARED_DEVICE_MULTI_ACCOUNT",
        "name": "Multiple Accounts Operating from Shared Device",
        "description": "Device fingerprint associated with 3 or more distinct accounts",
        "category": "DEVICE",
        "severity": "MEDIUM",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"min_accounts": 3}),
        "lookback_window_minutes": 1440,
        "version": 1
    },
    {
        "id": "RULE-BEN-05",
        "rule_code": "NEW_BENEFICIARY_SPIKE",
        "name": "Unusual Amount Sent to First-Time Beneficiary",
        "description": "First-time counterparty transfer exceeding $5,000",
        "category": "AMOUNT",
        "severity": "MEDIUM",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"min_amount": 5000.0}),
        "lookback_window_minutes": 43200,
        "version": 1
    },
    {
        "id": "RULE-REV-06",
        "rule_code": "REPEATED_REVERSALS",
        "name": "Repeated Transaction Reversals",
        "description": "Multiple reversed or failed transactions followed by transfer",
        "category": "VELOCITY",
        "severity": "HIGH",
        "is_enabled": 1,
        "thresholds_json": json.dumps({"min_reversals": 2}),
        "lookback_window_minutes": 1440,
        "version": 1
    }
]

def ensure_default_rules(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM detection_rules")
    if cursor.fetchone()[0] == 0:
        from app.utils.time import utc_now_iso
        now = utc_now_iso()
        for r in DEFAULT_RULES:
            cursor.execute("""
                INSERT INTO detection_rules (id, rule_code, name, description, category, severity, is_enabled, thresholds_json, lookback_window_minutes, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r["id"], r["rule_code"], r["name"], r["description"], r["category"], r["severity"], r["is_enabled"], r["thresholds_json"], r["lookback_window_minutes"], r["version"], now, now))
        conn.commit()

def evaluate_rules(conn: sqlite3.Connection, txn: Dict[str, Any], features: Dict[str, Any]) -> List[Dict[str, Any]]:
    ensure_default_rules(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id, rule_code, name, description, category, severity, thresholds_json, version FROM detection_rules WHERE is_enabled = 1")
    rows = cursor.fetchall()
    
    triggered = []
    amount = float(txn["amount"])
    
    for row in rows:
        r_id, code, name, desc, cat, severity, thresh_json, ver = row
        thresholds = safe_json_loads(thresh_json, {})
        is_hit = False
        evidence_fact = {}
        contrib = 0.0
        
        if code == "HIGH_VELOCITY_TRANSFERS":
            limit = thresholds.get("max_count_10m", 4)
            cnt = features.get("short_window_count", 1)
            if cnt > limit:
                is_hit = True
                contrib = 35.0
                evidence_fact = {"observed_count": cnt, "threshold": limit}
                
        elif code == "RAPID_FUND_MOVEMENT":
            min_in = thresholds.get("min_inbound", 5000.0)
            ratio = thresholds.get("forwarding_ratio", 0.80)
            recent_in = float(features.get("recent_inbound_sum") or features.get("total_inbound") or 0.0)
            if recent_in >= min_in and (amount / recent_in) >= ratio:
                is_hit = True
                contrib = 50.0
                evidence_fact = {"recent_inbound": recent_in, "forwarded_amount": amount, "ratio": round(amount / recent_in, 2)}
                
        elif code == "DORMANT_ACCOUNT_REACTIVATION":
            min_amt = thresholds.get("min_amount", 2000.0)
            if features.get("is_dormant_account", 0) == 1 and amount >= min_amt:
                is_hit = True
                contrib = 40.0
                evidence_fact = {"dormant_flag": 1, "amount": amount, "threshold": min_amt}
                
        elif code == "SHARED_DEVICE_MULTI_ACCOUNT":
            min_acc = thresholds.get("min_accounts", 3)
            acc_cnt = features.get("shared_device_accounts", 1)
            if acc_cnt >= min_acc:
                is_hit = True
                contrib = 25.0
                evidence_fact = {"shared_accounts": acc_cnt, "device_id": txn.get("device_id")}
                
        elif code == "NEW_BENEFICIARY_SPIKE":
            min_amt = thresholds.get("min_amount", 5000.0)
            if features.get("is_new_beneficiary", 0) == 1 and amount >= min_amt:
                is_hit = True
                contrib = 30.0
                evidence_fact = {"is_new_beneficiary": 1, "amount": amount, "threshold": min_amt}
                
        elif code == "REPEATED_REVERSALS":
            min_rev = thresholds.get("min_reversals", 2)
            rev_cnt = features.get("reversal_count", 0)
            if rev_cnt >= min_rev:
                is_hit = True
                contrib = 30.0
                evidence_fact = {"reversals_count": rev_cnt}

        if is_hit:
            triggered.append({
                "rule_id": r_id,
                "rule_code": code,
                "name": name,
                "description": desc,
                "severity": severity,
                "version": f"v{ver}",
                "score_contribution": contrib,
                "feature_values": evidence_fact
            })
            
    return triggered
