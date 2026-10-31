import sqlite3
from typing import Dict, Any, List

def _normalize_max_hops(hops: Any) -> int:
    if hasattr(hops, "default"):
        hops = hops.default
    try:
        val = int(hops)
    except (TypeError, ValueError):
        val = 2
    return max(1, min(val, 5))


def build_investigation_subgraph(
    conn: sqlite3.Connection,
    account_ids: List[str],
    max_hops: int = 2
) -> Dict[str, Any]:
    max_hops = _normalize_max_hops(max_hops)
    nodes = {}
    edges = {}
    
    # Bound input seed accounts to prevent combinatorial explosion
    seed_accounts = [a for a in account_ids if a][:5]
    visited_accounts = set(seed_accounts)
    frontier = set(seed_accounts)
    
    cursor = conn.cursor()
    
    # 1. Batch load initial account nodes and their customers
    if seed_accounts:
        acc_placeholders = ','.join(['?'] * len(seed_accounts))
        cursor.execute(f"""
            SELECT a.id, a.account_number, a.balance, a.currency, a.is_dormant, c.id as cust_id, c.full_name, c.risk_tier
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.id IN ({acc_placeholders})
        """, seed_accounts)
        
        for row in cursor.fetchall():
            acc_id = row['id']
            nodes[acc_id] = {
                "id": acc_id,
                "label": f"Account {row['account_number']}",
                "type": "ACCOUNT",
                "risk_level": "HIGH" if row["is_dormant"] else "LOW",
                "properties": {
                    "balance": float(row["balance"]) if row["balance"] is not None else 0.0,
                    "currency": row["currency"],
                    "dormant": bool(row["is_dormant"])
                }
            }
            cust_id = row["cust_id"]
            if cust_id not in nodes:
                nodes[cust_id] = {
                    "id": cust_id,
                    "label": f"Customer: {row['full_name']}",
                    "type": "CUSTOMER",
                    "risk_level": row["risk_tier"],
                    "properties": {"name": row["full_name"], "risk_tier": row["risk_tier"]}
                }
            e_id = f"owns_{cust_id}_{acc_id}"
            edges[e_id] = {
                "id": e_id,
                "source": cust_id,
                "target": acc_id,
                "type": "OWNS",
                "properties": {}
            }
            
    # 2. Expand hops via high-speed batch transaction queries
    for _ in range(max_hops):
        if not frontier:
            break
        # Bound frontier to top 8 accounts per hop for sub-second graph response
        curr_frontier = list(frontier)[:8]
        next_frontier = set()
        
        ph = ','.join(['?'] * len(curr_frontier))
        
        # Batch outbound transfers
        cursor.execute(f"""
            SELECT id, source_account_id, destination_account_id, beneficiary_name, amount, currency, created_at, device_id, ip_address
            FROM transactions
            WHERE source_account_id IN ({ph})
            ORDER BY created_at DESC LIMIT 50
        """, curr_frontier)
        
        out_rows = cursor.fetchall()
        for r in out_rows:
            txn_id = r["id"]
            curr_acc = r["source_account_id"]
            dest_acc = r["destination_account_id"]
            ben_name = r["beneficiary_name"]
            dev_id = r["device_id"]
            amt = float(r["amount"])
            
            # Device node
            if dev_id and dev_id not in nodes:
                nodes[dev_id] = {
                    "id": dev_id,
                    "label": f"Device {dev_id[:8]}",
                    "type": "DEVICE",
                    "risk_level": "LOW",
                    "properties": {}
                }
                e_dev = f"dev_{curr_acc}_{dev_id}"
                edges[e_dev] = {
                    "id": e_dev,
                    "source": curr_acc,
                    "target": dev_id,
                    "type": "USES_DEVICE",
                    "properties": {}
                }
                
            target_node_id = dest_acc or f"BEN-{ben_name}"
            if target_node_id and target_node_id not in nodes:
                nodes[target_node_id] = {
                    "id": target_node_id,
                    "label": f"Beneficiary: {ben_name or dest_acc}",
                    "type": "ACCOUNT" if dest_acc else "BENEFICIARY",
                    "risk_level": "MEDIUM",
                    "properties": {"name": ben_name or dest_acc}
                }
                if dest_acc and dest_acc not in visited_accounts:
                    next_frontier.add(dest_acc)
                    visited_accounts.add(dest_acc)
                    
            e_flow = f"flow_{curr_acc}_{target_node_id}_{txn_id}"
            edges[e_flow] = {
                "id": e_flow,
                "source": curr_acc,
                "target": target_node_id,
                "type": "TRANSFERS_TO",
                "amount": amt,
                "currency": r["currency"],
                "timestamp": str(r["created_at"]),
                "properties": {"transaction_id": txn_id}
            }
            
        # Batch inbound transfers
        cursor.execute(f"""
            SELECT id, source_account_id, destination_account_id, amount, currency, created_at
            FROM transactions
            WHERE destination_account_id IN ({ph})
            ORDER BY created_at DESC LIMIT 50
        """, curr_frontier)
        
        in_rows = cursor.fetchall()
        for r in in_rows:
            src_acc = r["source_account_id"]
            curr_acc = r["destination_account_id"]
            amt = float(r["amount"])
            txn_id = r["id"]
            if src_acc not in nodes:
                nodes[src_acc] = {
                    "id": src_acc,
                    "label": f"Account {src_acc}",
                    "type": "ACCOUNT",
                    "risk_level": "LOW",
                    "properties": {}
                }
                if src_acc not in visited_accounts:
                    next_frontier.add(src_acc)
                    visited_accounts.add(src_acc)
                    
            e_in = f"flow_{src_acc}_{curr_acc}_{txn_id}"
            edges[e_in] = {
                "id": e_in,
                "source": src_acc,
                "target": curr_acc,
                "type": "TRANSFERS_TO",
                "amount": amt,
                "currency": r["currency"],
                "timestamp": str(r["created_at"]),
                "properties": {"transaction_id": txn_id}
            }
            
        frontier = next_frontier
        
    cursor.close()
    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values())
    }
