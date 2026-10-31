import sqlite3
from typing import Dict, Any, List, Optional
from app.graph.builder import build_investigation_subgraph
from app.graph.traversal import find_shortest_path
from app.graph.suspicious_paths import detect_suspicious_patterns

def get_graph_for_investigation(conn: sqlite3.Connection, investigation_id: str, max_hops: int = 2) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.account_id
        FROM investigation_alerts ia
        JOIN alerts a ON ia.alert_id = a.id
        WHERE ia.investigation_id = ?
    """, (investigation_id,))
    account_ids = [r[0] for r in cursor.fetchall() if r[0]]
    
    if not account_ids:
        # Fallback to general accounts
        cursor.execute("SELECT account_id FROM alerts ORDER BY risk_score DESC LIMIT 5")
        account_ids = [r[0] for r in cursor.fetchall() if r[0]]
        if not account_ids:
            cursor.execute("SELECT id FROM accounts LIMIT 5")
            account_ids = [r[0] for r in cursor.fetchall()]
        
    return build_investigation_subgraph(conn, account_ids, max_hops=max_hops)

def expand_node_subgraph(conn: sqlite3.Connection, node_id: str, max_hops: int = 1) -> Dict[str, Any]:
    return build_investigation_subgraph(conn, [node_id], max_hops=max_hops)

def get_suspicious_clusters_and_paths(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    return detect_suspicious_patterns(conn)
