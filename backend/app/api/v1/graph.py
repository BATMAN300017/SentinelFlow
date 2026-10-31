from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional, List
from app.api.dependencies import get_db
from app.services.graph_service import (
    get_graph_for_investigation, expand_node_subgraph, get_suspicious_clusters_and_paths
)
from app.schemas.graph import GraphExpandRequest, PathFindRequest
from app.graph.traversal import find_shortest_path

router = APIRouter()

@router.get("")
def get_graph(
    investigation_id: Optional[str] = None,
    account_id: Optional[str] = None,
    hops: int = Query(2, ge=1, le=3),
    db: sqlite3.Connection = Depends(get_db)
):
    from app.graph.builder import build_investigation_subgraph
    if account_id:
        return build_investigation_subgraph(db, [account_id], max_hops=hops)
    if investigation_id:
        from app.services.graph_service import get_graph_for_investigation
        return get_graph_for_investigation(db, investigation_id, max_hops=hops)
    # Return graph built from active alerts or accounts
    cursor = db.cursor()
    cursor.execute("SELECT account_id FROM alerts ORDER BY risk_score DESC LIMIT 5")
    accounts = [r[0] for r in cursor.fetchall() if r[0]]
    if not accounts:
        cursor.execute("SELECT id FROM accounts LIMIT 5")
        accounts = [r[0] for r in cursor.fetchall()]
    return build_investigation_subgraph(db, accounts, max_hops=hops)

@router.post("/expand")
def post_expand_graph(req: GraphExpandRequest, db: sqlite3.Connection = Depends(get_db)):
    return expand_node_subgraph(db, req.node_id, max_hops=req.max_hops)

@router.post("/paths")
def post_find_paths(req: PathFindRequest, db: sqlite3.Connection = Depends(get_db)):
    from app.graph.builder import build_investigation_subgraph
    subgraph = build_investigation_subgraph(db, [req.source_node_id, req.target_node_id], max_hops=req.max_depth)
    path = find_shortest_path(subgraph["edges"], req.source_node_id, req.target_node_id, max_depth=req.max_depth)
    return {
        "source": req.source_node_id,
        "target": req.target_node_id,
        "found": path is not None,
        "path": path or [],
        "subgraph": subgraph
    }

@router.get("/clusters")
def get_graph_clusters(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM accounts LIMIT 20")
    accounts = [r[0] for r in cursor.fetchall()]
    from app.graph.builder import build_investigation_subgraph
    from app.graph.communities import compute_connected_components
    subgraph = build_investigation_subgraph(db, accounts, max_hops=1)
    clusters = compute_connected_components(subgraph["nodes"], subgraph["edges"])
    return {
        "cluster_count": len(clusters),
        "clusters": clusters
    }

@router.get("/suspicious-paths")
def get_suspicious_paths(db: sqlite3.Connection = Depends(get_db)):
    return get_suspicious_clusters_and_paths(db)

@router.get("/mule-networks", summary="Discover money mule networks, chains, and topological patterns")
def get_mule_networks(db: sqlite3.Connection = Depends(get_db)):
    from app.graph.mule_network_engine import MuleNetworkEngine
    engine = MuleNetworkEngine(db)
    return engine.get_full_topology_report()
