import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from app.api.dependencies import get_db
from app.core.logging import logger

router = APIRouter()

@router.get("", summary="Retrieve dynamic Sankey fund flow tracing network")
def get_fund_flow(
    account_id: Optional[str] = Query(None, description="Focus on a specific account ID"),
    transaction_id: Optional[str] = Query(None, description="Focus on a specific transaction ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    start_date: Optional[str] = Query(None, description="Custom start date (ISO string)"),
    end_date: Optional[str] = Query(None, description="Custom end date (ISO string)"),
    currency: Optional[str] = Query("INR", description="Currency filter (INR, GBP, USD, EUR, ALL)"),
    direction: Optional[str] = Query("both", pattern="^(both|forward|backward)$"),
    min_amount: Optional[float] = Query(None, ge=0),
    limit: int = Query(25, ge=5, le=100),
    db: sqlite3.Connection = Depends(get_db)
) -> Dict[str, Any]:
    """
    Computes an empirical, multi-hop money-flow Sankey network directly from genuine transaction records.
    Constructs 3 tiers:
      - Source accounts (Originators / Ingress)
      - Intermediary accounts (Transit / Layering Mules / Switches)
      - Destination accounts (Beneficiaries / Cash-out / Off-ramps)
    """
    account_id = account_id.default if hasattr(account_id, "default") else account_id
    transaction_id = transaction_id.default if hasattr(transaction_id, "default") else transaction_id
    days = (days.default if hasattr(days, "default") else days) or 30
    start_date = start_date.default if hasattr(start_date, "default") else start_date
    end_date = end_date.default if hasattr(end_date, "default") else end_date
    currency = (currency.default if hasattr(currency, "default") else currency) or "INR"
    direction = (direction.default if hasattr(direction, "default") else direction) or "both"
    min_amount = min_amount.default if hasattr(min_amount, "default") else min_amount
    limit = (limit.default if hasattr(limit, "default") else limit) or 25

    cursor = db.cursor()
    
    conditions = [
        "t.destination_account_id IS NOT NULL",
        "t.source_account_id IS NOT NULL",
        "t.source_account_id != t.destination_account_id"
    ]
    params: List[Any] = []

    if currency and currency.upper() != "ALL":
        conditions.append("t.currency = ?")
        params.append(currency.upper())

    if min_amount is not None:
        conditions.append("t.amount >= ?")
        params.append(float(min_amount))

    if account_id:
        if direction == "forward":
            conditions.append("t.source_account_id = ?")
            params.append(account_id)
        elif direction == "backward":
            conditions.append("t.destination_account_id = ?")
            params.append(account_id)
        else:
            conditions.append("(t.source_account_id = ? OR t.destination_account_id = ?)")
            params.extend([account_id, account_id])

    if transaction_id:
        conditions.append("t.id = ?")
        params.append(transaction_id)

    where_clause = " AND ".join(conditions)

    # 1. Fetch primary high-signal transactions
    query = f"""
        SELECT t.id, t.source_account_id, t.destination_account_id,
               t.amount, t.currency, t.risk_score, t.payment_channel,
               t.status, t.created_at, t.dataset_source, t.is_ground_truth_fraud
        FROM transactions t
        WHERE {where_clause}
        ORDER BY t.risk_score DESC, t.amount DESC
        LIMIT ?
    """
    params.append(limit * 3)
    cursor.execute(query, params)
    txns = [dict(r) for r in cursor.fetchall()]

    if not txns:
        return {
            "currency": currency,
            "period_days": days,
            "period_label": f"Last {days} days",
            "summary": {
                "total_volume": 0.0,
                "flow_count": 0,
                "node_count": 0,
                "intermediaries_count": 0
            },
            "nodes": [],
            "links": []
        }

    # 2. Extract account volumes and identify pass-through intermediaries
    account_inflow: Dict[str, float] = {}
    account_outflow: Dict[str, float] = {}
    for t in txns:
        src = t["source_account_id"]
        dst = t["destination_account_id"]
        amt = float(t.get("amount") or 0.0)
        account_outflow[src] = account_outflow.get(src, 0.0) + amt
        account_inflow[dst] = account_inflow.get(dst, 0.0) + amt

    intermediary_candidates = set(account_inflow.keys()).intersection(set(account_outflow.keys()))

    # If no natural intermediaries in initial slice, expand downstream connections from top destinations
    if not intermediary_candidates and len(txns) > 0 and not account_id:
        dest_sample = list(set(t["destination_account_id"] for t in txns))[:12]
        placeholders = ",".join(["?"] * len(dest_sample))
        cursor.execute(f"""
            SELECT t.id, t.source_account_id, t.destination_account_id,
                   t.amount, t.currency, t.risk_score, t.payment_channel,
                   t.status, t.created_at, t.dataset_source, t.is_ground_truth_fraud
            FROM transactions t
            WHERE t.source_account_id IN ({placeholders})
              AND t.destination_account_id IS NOT NULL
            LIMIT 30
        """, dest_sample)
        leg2_txns = [dict(r) for r in cursor.fetchall()]
        if leg2_txns:
            txns.extend(leg2_txns)
            for t in leg2_txns:
                src = t["source_account_id"]
                dst = t["destination_account_id"]
                amt = float(t.get("amount") or 0.0)
                account_outflow[src] = account_outflow.get(src, 0.0) + amt
                account_inflow[dst] = account_inflow.get(dst, 0.0) + amt
            intermediary_candidates = set(account_inflow.keys()).intersection(set(account_outflow.keys()))

    # 3. Aggregate distinct flows
    flows: Dict[tuple, Dict[str, Any]] = {}
    for t in txns:
        key = (t["source_account_id"], t["destination_account_id"])
        amt = float(t.get("amount") or 0.0)
        if key not in flows:
            flows[key] = {
                "source": t["source_account_id"],
                "target": t["destination_account_id"],
                "value": 0.0,
                "currency": t.get("currency") or "INR",
                "count": 0,
                "max_risk_score": 0.0,
                "transactions": []
            }
        flows[key]["value"] += amt
        flows[key]["count"] += 1
        flows[key]["max_risk_score"] = max(flows[key]["max_risk_score"], float(t.get("risk_score") or 0.0))
        if len(flows[key]["transactions"]) < 12:
            flows[key]["transactions"].append({
                "id": t["id"],
                "amount": float(t.get("amount") or 0.0),
                "currency": t.get("currency"),
                "risk_score": float(t.get("risk_score") or 0.0),
                "created_at": str(t.get("created_at")),
                "channel": t.get("payment_channel"),
                "status": t.get("status"),
                "dataset_source": t.get("dataset_source")
            })

    sorted_links = sorted(flows.values(), key=lambda x: x["value"], reverse=True)[:limit]

    # 4. Classify nodes into Source, Intermediary, and Destination tiers
    active_nodes: Dict[str, Dict[str, Any]] = {}
    for l in sorted_links:
        src = l["source"]
        tgt = l["target"]
        for acc in [src, tgt]:
            if acc not in active_nodes:
                is_inter = acc in intermediary_candidates
                is_src_only = account_outflow.get(acc, 0.0) > 0 and account_inflow.get(acc, 0.0) == 0
                tier = "intermediary" if is_inter else ("source" if is_src_only else "destination")
                
                # Assign risk level based on max flow risk
                node_risk = "LOW"
                if l["max_risk_score"] >= 80:
                    node_risk = "CRITICAL"
                elif l["max_risk_score"] >= 50:
                    node_risk = "HIGH"
                elif l["max_risk_score"] >= 25:
                    node_risk = "MEDIUM"

                active_nodes[acc] = {
                    "id": acc,
                    "name": acc,
                    "tier": tier,
                    "risk_level": node_risk,
                    "total_inflow": round(account_inflow.get(acc, 0.0), 2),
                    "total_outflow": round(account_outflow.get(acc, 0.0), 2),
                    "net_flow": round(account_inflow.get(acc, 0.0) - account_outflow.get(acc, 0.0), 2),
                    "currency": l["currency"]
                }

    total_vol = round(sum(l["value"] for l in sorted_links), 2)
    period_str = f"Last {days} days"
    if start_date and end_date:
        period_str = f"{start_date[:10]} to {end_date[:10]}"

    return {
        "currency": currency,
        "period_days": days,
        "period_label": period_str,
        "summary": {
            "total_volume": total_vol,
            "flow_count": len(sorted_links),
            "node_count": len(active_nodes),
            "intermediaries_count": len([n for n in active_nodes.values() if n["tier"] == "intermediary"])
        },
        "nodes": list(active_nodes.values()),
        "links": sorted_links
    }
