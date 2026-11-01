from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional
from app.api.dependencies import get_db
from app.repositories.transaction_repository import list_transactions, get_transaction_by_id
from app.detection.engine import score_transaction
from app.graph.builder import build_investigation_subgraph
from app.services.route_map_service import get_scam_and_route_dossier

router = APIRouter()

@router.get("")
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    limit: Optional[int] = Query(None),
    risk_band: Optional[str] = None,
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    channel: Optional[str] = None,
    dataset: Optional[str] = None,
    min_score: Optional[float] = None,
    flow_status: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    limit_val = limit.default if hasattr(limit, "default") else limit
    page_val = (page.default if hasattr(page, "default") else page) or 1
    page_size_val = (page_size.default if hasattr(page_size, "default") else page_size) or 50

    effective_limit = int(limit_val) if limit_val is not None else int(page_size_val)
    page_int = int(page_val)
    offset = (page_int - 1) * effective_limit

    items, total = list_transactions(
        db,
        limit=effective_limit,
        offset=offset,
        risk_band=risk_band,
        account_id=account_id,
        search=search,
        channel=channel,
        dataset=dataset,
        min_score=min_score,
        flow_status=flow_status
    )
    return {
        "items": items,
        "total": total,
        "page": page_int,
        "page_size": effective_limit,
        "total_pages": (total + effective_limit - 1) // effective_limit if effective_limit > 0 else 1
    }

@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return txn

@router.get("/{transaction_id}/case")
def get_transaction_case(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Returns the associated investigation dossier or generates a dynamic investigative case
    for this transaction with full evidentiary breakdown and route map.
    """
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    # If already linked to an alert or investigation
    alert_id = txn.get("linked_alert_id")
    inv_id = txn.get("linked_investigation_id")
    
    dossier = get_scam_and_route_dossier(db, alert_id=alert_id, investigation_id=inv_id)
    return {
        "transaction": txn,
        "linked_alert_id": alert_id,
        "linked_investigation_id": inv_id,
        "dossier": dossier
    }

@router.get("/{transaction_id}/risk")
def get_transaction_risk_analysis(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    res = score_transaction(db, txn)
    return {
        "transaction_id": txn["id"],
        **res
    }

@router.get("/{transaction_id}/relationships")
def get_transaction_relationships(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    accounts = [txn["source_account_id"]]
    if txn.get("destination_account_id"):
        accounts.append(txn["destination_account_id"])
    return build_investigation_subgraph(db, accounts, max_hops=1)
