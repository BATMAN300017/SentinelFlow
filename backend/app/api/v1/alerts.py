from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import sqlite3
from typing import Optional
from app.api.dependencies import get_db, get_current_user, require_permission
from app.core.permissions import Permission
from app.core.logging import logger
from app.utils.time import utc_now_iso
from app.repositories.alert_repository import list_alerts, get_alert_by_id
from app.schemas.alert import AlertAssignRequest, AlertTriageRequest, AlertDismissRequest, AlertInvestigateRequest
from app.services.alert_service import assign_alert, triage_alert, dismiss_alert, convert_alert_to_investigation
from app.services.route_map_service import get_scam_and_route_dossier

router = APIRouter()

@router.get("")
def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    dataset: Optional[str] = None,
    detection_method: Optional[str] = None,
    search: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    items, total = list_alerts(
        db,
        limit=page_size,
        offset=offset,
        severity=severity,
        status=status,
        dataset=dataset,
        detection_method=detection_method,
        search=search
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }

@router.get("/{alert_id}")
def get_alert(alert_id: str, db: sqlite3.Connection = Depends(get_db)):
    alt = get_alert_by_id(db, alert_id)
    if not alt:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": {"code": "ALERT_NOT_FOUND", "message": f"Alert {alert_id} not found"}}
        )
    return alt

@router.post("/{alert_id}/assign")
def post_assign_alert(
    alert_id: str,
    req: AlertAssignRequest,
    current_user: dict = Depends(require_permission(Permission.TRIAGE_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return assign_alert(db, alert_id, req.user_id, current_user.get("full_name", "Investigator"))

@router.post("/{alert_id}/triage")
def post_triage_alert(
    alert_id: str,
    req: AlertTriageRequest,
    current_user: dict = Depends(require_permission(Permission.TRIAGE_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return triage_alert(db, alert_id, req.severity, req.notes, current_user.get("full_name", "Investigator"))

@router.post("/{alert_id}/dismiss")
def post_dismiss_alert(
    alert_id: str,
    req: AlertDismissRequest,
    current_user: dict = Depends(require_permission(Permission.DISMISS_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return dismiss_alert(db, alert_id, req.reason, current_user.get("full_name", "Investigator"))

@router.get("/{alert_id}/scam-dossier")
def get_alert_scam_dossier(alert_id: str, db: sqlite3.Connection = Depends(get_db)):
    dossier = get_scam_and_route_dossier(db, alert_id=alert_id)
    if "error" in dossier:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": {"code": "DOSSIER_NOT_FOUND", "message": dossier["error"]}}
        )
    return dossier

@router.post("/{alert_id}/investigate")
def post_convert_investigation(
    alert_id: str,
    current_user: dict = Depends(require_permission(Permission.CREATE_INVESTIGATION)),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        res = convert_alert_to_investigation(db, alert_id, current_user.get("full_name", "Investigator"))
        if not res or "error" in res:
            err_msg = res.get("error", "Failed to convert alert to investigation") if res else "Unknown error"
            return JSONResponse(
                status_code=404 if "not found" in err_msg.lower() else 400,
                content={"success": False, "error": {"code": "INVESTIGATION_FAILED", "message": err_msg}}
            )
            
        inv_id = res.get("investigation_id")
        dossier = get_scam_and_route_dossier(db, investigation_id=inv_id, alert_id=alert_id)
        
        # Build network graph summary from verified hops
        hops = dossier.get("route_map", {}).get("hops", [])
        network_nodes = []
        network_links = []
        for i, hop in enumerate(hops):
            network_nodes.append({
                "id": hop.get("node_id"),
                "account_id": hop.get("account_id"),
                "type": hop.get("node_type"),
                "channel": hop.get("channel"),
                "verified_country": hop.get("verified_country")
            })
            if i > 0:
                network_links.append({
                    "source": hops[i-1].get("node_id"),
                    "target": hop.get("node_id"),
                    "amount": hop.get("amount"),
                    "currency": hop.get("currency")
                })

        investigation_obj = {
            "investigation_id": inv_id,
            "case_number": dossier.get("case_number") or f"CASE-{inv_id[-6:].upper()}",
            "alert_id": alert_id,
            "transaction_id": dossier.get("transaction", {}).get("id") or res.get("transaction_id"),
            "account_id": dossier.get("transaction", {}).get("source_account_id") or res.get("account_id"),
            "destination_account_id": dossier.get("transaction", {}).get("destination_account_id"),
            "risk_score": float(dossier.get("risk_score") or 0.0),
            "findings": dossier.get("findings", []),
            "network": {
                "nodes": network_nodes,
                "links": network_links,
                "total_hops": len(hops)
            },
            "status": "completed",
            "case_title": res.get("case_title"),
            "created_at": utc_now_iso()
        }
        
        return {
            "success": True,
            "investigation": investigation_obj,
            "scam_dossier": dossier,
            "investigation_id": inv_id,
            "status": "COMPLETED"
        }
    except Exception as e:
        logger.error(f"Error in post_convert_investigation for {alert_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )
