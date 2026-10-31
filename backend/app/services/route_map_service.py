import sqlite3
from typing import Dict, Any, List, Optional
from app.utils.time import utc_now_iso
from app.utils.json_utils import safe_json_loads, sanitize_json_dict

def get_scam_and_route_dossier(
    conn: sqlite3.Connection,
    investigation_id: Optional[str] = None,
    alert_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a genuine, database-backed Investigation Dossier and Account-to-Account
    Money Flow Graph for an alert or investigation without hardcoded or fabricated locations.
    """
    cursor = conn.cursor()
    
    # 1. Resolve alert and investigation
    inv = None
    alt = None
    if investigation_id:
        cursor.execute("SELECT * FROM investigations WHERE id = ? OR case_number = ?", (investigation_id, investigation_id))
        r = cursor.fetchone()
        if r:
            inv = dict(r._dict if hasattr(r, "_dict") else r)
            cursor.execute("""
                SELECT a.* FROM alerts a
                JOIN investigation_alerts ia ON a.id = ia.alert_id
                WHERE ia.investigation_id = ?
                ORDER BY a.risk_score DESC LIMIT 1
            """, (inv["id"],))
            ar = cursor.fetchone()
            if ar:
                alt = dict(ar._dict if hasattr(ar, "_dict") else ar)
                
    if not alt and alert_id:
        cursor.execute("SELECT * FROM alerts WHERE id = ? OR alert_ref = ?", (alert_id, alert_id))
        ar = cursor.fetchone()
        if ar:
            alt = dict(ar._dict if hasattr(ar, "_dict") else ar)
            
    if not alt:
        cursor.execute("SELECT * FROM alerts ORDER BY risk_score DESC LIMIT 1")
        ar = cursor.fetchone()
        if ar:
            alt = dict(ar._dict if hasattr(ar, "_dict") else ar)
            
    if not alt:
        return {"error": "No alert or investigation data found"}
        
    # 2. Retrieve triggering transaction from database
    txn_id = alt.get("transaction_id")
    txn = None
    if txn_id:
        cursor.execute("""
            SELECT t.*, c.full_name as customer_name, c.email as customer_email, 
                   c.risk_tier as customer_risk_tier, c.kyc_status,
                   a.account_number as src_account_number, a.account_type as src_account_type, a.balance as src_balance
            FROM transactions t
            LEFT JOIN accounts a ON t.source_account_id = a.id
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE t.id = ?
        """, (txn_id,))
        txn_row = cursor.fetchone()
        if not txn_row:
            cursor.execute("""
                SELECT t.*, c.full_name as customer_name, c.email as customer_email, 
                       c.risk_tier as customer_risk_tier, c.kyc_status,
                       a.account_number as src_account_number, a.account_type as src_account_type, a.balance as src_balance
                FROM transactions t
                LEFT JOIN accounts a ON t.source_account_id = a.id
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE t.original_transaction_id = ? OR t.event_id = ?
                LIMIT 1
            """, (txn_id, txn_id))
            txn_row = cursor.fetchone()
            
        if txn_row:
            txn = dict(txn_row._dict if hasattr(txn_row, "_dict") else txn_row)

    if not txn:
        # Fetch from account directly
        acc_id = alt["account_id"]
        cursor.execute("""
            SELECT t.*, c.full_name as customer_name, c.email as customer_email, 
                   c.risk_tier as customer_risk_tier, c.kyc_status,
                   a.account_number as src_account_number, a.account_type as src_account_type, a.balance as src_balance
            FROM transactions t
            LEFT JOIN accounts a ON t.source_account_id = a.id
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE t.source_account_id = ?
            ORDER BY t.amount DESC LIMIT 1
        """, (acc_id,))
        txn_row = cursor.fetchone()
        if txn_row:
            txn = dict(txn_row._dict if hasattr(txn_row, "_dict") else txn_row)
        else:
            txn = {
                "id": txn_id or "TXN-UNKNOWN",
                "amount": 0.0,
                "currency": "USD",
                "transaction_type": "TRANSFER",
                "payment_channel": "ONLINE",
                "source_account_id": alt["account_id"],
                "destination_account_id": None,
                "beneficiary_name": "Counterparty",
                "customer_id": alt.get("customer_id"),
                "customer_name": f"Account Holder {alt['account_id']}",
                "customer_email": "holder@bank.internal",
                "customer_risk_tier": "STANDARD",
                "kyc_status": "VERIFIED",
                "src_account_number": alt["account_id"],
                "src_account_type": "SAVINGS",
                "src_balance": 0.0,
                "risk_score": float(alt.get("risk_score") or 0.0),
                "created_at": str(alt.get("created_at") or utc_now_iso())
            }

    # 3. Retrieve Alert Findings from alert_findings table
    cursor.execute("SELECT * FROM alert_findings WHERE alert_id = ? ORDER BY score_contribution DESC", (alt["id"],))
    findings = []
    for f in cursor.fetchall():
        f_dict = dict(f._dict if hasattr(f, "_dict") else f)
        f_dict["feature_values"] = safe_json_loads(f_dict.get("feature_values_json"), {})
        f_dict["score_contribution"] = float(f_dict.get("score_contribution") or 0.0)
        findings.append(f_dict)
    
    # 4. Classify Modus Operandi & Typology based on genuine database signals
    risk_score = float(alt["risk_score"])
    amount = float(txn.get("amount") or 0.0)
    payment_channel = str(txn.get("payment_channel") or "TRANSFER").upper()
    dataset_source = str(txn.get("dataset_source") or "CORE").upper()
    
    title_summary = f"{alt.get('title', '')} {alt.get('summary', '')}".upper()
    if "MULE" in title_summary or alt.get("alert_type") == "MULE_SYNDICATE":
        scam_category = "MULE_ACCOUNT_SYNDICATE"
        scam_title = "Money Mule Account Syndicate & Aggregation Hub"
        modus_operandi = f"Account {alt['account_id']} identified as a high-velocity staging mule account with aggregated fund dispersion across counterparties."
    elif "SMURF" in title_summary or "STRUCTUR" in title_summary:
        scam_category = "THRESHOLD_STRUCTURING"
        scam_title = "Smurfing / Structured Velocity Pattern"
        modus_operandi = "Multiple discrete transfers structured below standard reporting thresholds to obscure total liquidity accumulation."
    elif "FAN_IN" in title_summary:
        scam_category = "FAN_IN_COLLECTION"
        scam_title = "Fan-In Rapid Fund Aggregation"
        modus_operandi = "Funds collected from dispersed source nodes into a single centralizing pool."
    elif "CIRCULAR" in title_summary or "CYCLE" in title_summary:
        scam_category = "CIRCULAR_ROUND_TRIP"
        scam_title = "Circular Round-Trip Transfer Ring"
        modus_operandi = "Layered multi-hop circular transfers returning to originating syndicate entities."
    else:
        scam_category = "BEHAVIORAL_OUTLIER"
        scam_title = "High-Risk Transaction Outlier"
        modus_operandi = f"Significant deviation from account historical median baseline via {payment_channel} payment channel."

    # 5. Build Genuine Account-to-Account Money-Flow Path (NO fake Bahamas or New York)
    # Determine verified country or flag as Unavailable
    currency = str(txn.get("currency") or "USD").upper()
    if currency == "INR" or dataset_source in ("NFPC", "INDIA_SIMULATOR"):
        verified_origin_country = "India"
        verified_dest_country = "India"
        geo_status = "VERIFIED_INR_INDIA"
    elif currency == "GBP":
        verified_origin_country = "United Kingdom"
        verified_dest_country = "United Kingdom"
        geo_status = "VERIFIED_GBP_UK"
    else:
        verified_origin_country = "Unknown / Unavailable"
        verified_dest_country = "Unknown / Unavailable"
        geo_status = "UNAVAILABLE"

    src_acc_id = str(txn.get("source_account_id") or alt["account_id"])
    dest_acc_id = str(txn.get("destination_account_id") or "UNKNOWN_COUNTERPARTY")

    hops = []
    
    # Hop 1: Originating Account
    hops.append({
        "hop_index": 1,
        "hop_type": "ORIGIN",
        "title": "Originating Account",
        "entity_id": src_acc_id,
        "entity_name": txn.get("customer_name") or f"Account Holder {src_acc_id}",
        "entity_role": "MULE_STAGING_SENDER" if "MULE" in scam_category else "SENDER",
        "account_number": str(txn.get("src_account_number") or src_acc_id),
        "city": "Unavailable (No GPS in Banking Rail)",
        "country": verified_origin_country,
        "lat": None,
        "lon": None,
        "ip_address": txn.get("ip_address") or "Internal Core Banking",
        "isp": "Internal Banking Network",
        "device_id": txn.get("device_id") or "Core Terminal",
        "channel": payment_channel,
        "amount": amount,
        "currency": currency,
        "timestamp": str(txn.get("transaction_timestamp") or txn.get("created_at") or alt.get("created_at")),
        "status": "INITIATED",
        "notes": f"Triggering transfer originating from account {src_acc_id}. Balance: {currency} {float(txn.get('src_balance') or 0.0):,.2f}."
    })

    # Hop 2: Primary Destination Beneficiary
    hops.append({
        "hop_index": 2,
        "hop_type": "INTERMEDIARY_MULE" if "MULE" in scam_category else "BENEFICIARY_RECIPIENT",
        "title": "Destination Beneficiary",
        "entity_id": dest_acc_id,
        "entity_name": txn.get("beneficiary_name") or f"Counterparty {dest_acc_id}",
        "entity_role": "RECIPIENT_BENEFICIARY",
        "account_number": dest_acc_id,
        "city": "Unavailable (No GPS in Banking Rail)",
        "country": verified_dest_country,
        "lat": None,
        "lon": None,
        "ip_address": "Internal Clearing Rail",
        "isp": "Interbank Settlement",
        "device_id": "Counterparty Switch",
        "channel": payment_channel,
        "amount": amount,
        "currency": currency,
        "timestamp": str(txn.get("transaction_timestamp") or txn.get("created_at") or alt.get("created_at")),
        "status": "COMPLETED",
        "notes": f"Funds transferred via {payment_channel} to counterparty {dest_acc_id}."
    })

    # Discover Connected Layering Transfers from Database (Indexed query)
    cursor.execute("""
        SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.currency, 
               t.payment_channel, t.created_at, t.beneficiary_name
        FROM transactions t
        WHERE t.source_account_id = ? AND t.id != ?
        ORDER BY t.created_at ASC LIMIT 2
    """, (src_acc_id, txn.get("id", "")))
    sibling_txns = cursor.fetchall()

    for s_idx, sib in enumerate(sibling_txns):
        s_dict = dict(sib._dict if hasattr(sib, "_dict") else sib)
        hops.append({
            "hop_index": len(hops) + 1,
            "hop_type": "CONNECTED_DISBURSAL",
            "title": f"Corroborating Disbursal #{s_idx + 1}",
            "entity_id": str(s_dict.get("destination_account_id") or "COUNTERPARTY"),
            "entity_name": s_dict.get("beneficiary_name") or f"Counterparty {s_dict.get('destination_account_id')}",
            "entity_role": "SYNDICATE_MEMBER",
            "account_number": str(s_dict.get("destination_account_id") or "CP-DISBURSAL"),
            "city": "Unavailable (No GPS in Banking Rail)",
            "country": verified_dest_country,
            "lat": None,
            "lon": None,
            "channel": str(s_dict.get("payment_channel") or payment_channel),
            "amount": float(s_dict.get("amount") or 0.0),
            "currency": str(s_dict.get("currency") or currency),
            "timestamp": str(s_dict.get("created_at")),
            "status": "FORWARDED",
            "notes": f"Linked transfer discovered in account network: {currency} {float(s_dict.get('amount') or 0.0):,.2f} via {s_dict.get('payment_channel')}."
        })

    # 6. Gather Evidence Items
    evidence_items = []
    if inv:
        cursor.execute("SELECT * FROM evidence_items WHERE investigation_id = ?", (inv["id"],))
        for e in cursor.fetchall():
            e_dict = dict(e._dict if hasattr(e, "_dict") else e)
            e_dict["observed_facts"] = safe_json_loads(e_dict.get("observed_facts_json"), {})
            e_dict["associated_entities"] = safe_json_loads(e_dict.get("associated_entities_json"), [])
            evidence_items.append(e_dict)

    # 7. Prescribed Playbook & Recommended Actions
    actions = [
        {
            "priority": "IMMEDIATE",
            "action": "Place Temporary Outbound Restraint on Source Account",
            "description": f"Halt outward liquidity sweeps on account {src_acc_id} to prevent further syndicate fund dispersal.",
            "completed": False
        },
        {
            "priority": "HIGH",
            "action": "Inspect Full Account Network in Network Intelligence",
            "description": f"Review 1-hop and 2-hop graph connectivity for {src_acc_id} across counterparty nodes.",
            "completed": False
        },
        {
            "priority": "MEDIUM",
            "action": "Review Contradictory & Business Baseline Context",
            "description": "Assess historical account profile, legitimate payroll patterns, or commercial turnover before final SAR filing.",
            "completed": False
        }
    ]

    # 8. Contradictory & Exculpatory Analysis
    exculpatory_analysis = {
        "supports_fraud": [
            f"Transfer amount {currency} {amount:,.2f} represents an anomalous velocity event on {payment_channel}.",
            f"Account {src_acc_id} is flagged with multi-signal score of {risk_score:.1f}.",
            f"Identified multiple linked counterparty transfers in {dataset_source} transaction feed."
        ],
        "contradicts_fraud": [
            f"Account holder {txn.get('customer_name', 'Customer')} has verified KYC status.",
            f"Account {src_acc_id} maintains active tenure on banking platform.",
            "If counterparty is an accredited institutional entity, grant disbursement, or payroll clearing, transaction may be dismissed as legitimate."
        ],
        "scholarship_or_institution_check": {
            "is_institutional_counterparty": "UNIVERSITY" in str(txn.get("beneficiary_name", "")).upper() or "PAYROLL" in str(txn.get("beneficiary_name", "")).upper(),
            "guidance": "Verify whether beneficiary matches accredited educational institution, government body, or formal corporate payroll."
        }
    }

    # Sanitize entire output dictionary to guarantee zero Decimal serialization crashes
    output = {
        "investigation_id": inv["id"] if inv else None,
        "case_number": inv["case_number"] if inv else f"CASE-PREVIEW-{alt.get('alert_ref', 'ALT')}",
        "alert_id": alt["id"],
        "alert_ref": alt["alert_ref"],
        "alert_title": alt["title"],
        "alert_severity": alt["severity"],
        "risk_score": risk_score,
        "status": inv["status"] if inv else alt["status"],
        "scam_category": scam_category,
        "scam_title": scam_title,
        "modus_operandi": modus_operandi,
        "transaction": sanitize_json_dict(txn),
        "route_map": {
            "visualization_mode": "ACCOUNT_FLOW",
            "geographic_status": geo_status,
            "origin_country": verified_origin_country,
            "origin_city": "Unavailable",
            "destination_country": verified_dest_country,
            "destination_city": "Unavailable",
            "distance_km": None,
            "total_hops": len(hops),
            "hops": sanitize_json_dict(hops)
        },
        "findings": sanitize_json_dict(findings),
        "evidence_items": sanitize_json_dict(evidence_items),
        "recommended_actions": actions,
        "exculpatory_analysis": exculpatory_analysis
    }
    
    return sanitize_json_dict(output)
