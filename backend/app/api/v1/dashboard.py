import time
import threading
from typing import Optional, Tuple, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from app.utils.json_utils import safe_json_loads
from app.api.dependencies import get_db
from app.services.analytics_service import get_kpi_summary, get_analytics_trends
from app.core.logging import logger

router = APIRouter()

# In-memory thread-safe TTL caches for dashboard performance and connection preservation
_cache_lock = threading.Lock()
_summary_cache: Optional[Tuple[float, Dict[str, Any]]] = None
_trends_cache: Optional[Tuple[float, Dict[str, Any]]] = None
CACHE_TTL_SECONDS = 30.0

@router.get("/summary")
def get_dashboard_summary(db: sqlite3.Connection = Depends(get_db)):
    """
    Returns real-time fraud command center KPIs.
    Cached for 30s to prevent concurrent query contention and database timeout.
    """
    global _summary_cache
    now = time.time()
    with _cache_lock:
        if _summary_cache and (now - _summary_cache[0] < CACHE_TTL_SECONDS):
            return _summary_cache[1]
    
    try:
        data = get_kpi_summary(db)
        with _cache_lock:
            _summary_cache = (now, data)
        return data
    except Exception as e:
        logger.error(f"Error computing dashboard summary: {e}")
        with _cache_lock:
            if _summary_cache:
                logger.warning("Returning stale dashboard summary cache due to query exception.")
                return _summary_cache[1]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dashboard telemetry temporarily unavailable: {str(e)}"
        )

@router.get("/trends")
def get_dashboard_trends(db: sqlite3.Connection = Depends(get_db)):
    """
    Returns risk distribution and investigation trends.
    Cached for 30s to prevent connection exhaustion.
    """
    global _trends_cache
    now = time.time()
    with _cache_lock:
        if _trends_cache and (now - _trends_cache[0] < CACHE_TTL_SECONDS):
            return _trends_cache[1]
    
    try:
        data = get_analytics_trends(db)
        with _cache_lock:
            _trends_cache = (now, data)
        return data
    except Exception as e:
        logger.error(f"Error computing dashboard trends: {e}")
        with _cache_lock:
            if _trends_cache:
                logger.warning("Returning stale dashboard trends cache due to query exception.")
                return _trends_cache[1]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dashboard trends telemetry temporarily unavailable: {str(e)}"
        )

@router.get("/activity")
def get_recent_activity(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, actor_name, action, resource_type, resource_id, metadata_json, created_at
        FROM audit_events
        ORDER BY created_at DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    activities = []
    for r in rows:
        d = dict(r)
        d["metadata"] = safe_json_loads(d.get("metadata_json"), {})
        activities.append(d)
    return activities
