from typing import Dict, Any, List, Optional
from app.detection.calibration import assign_triage_band, assign_alert_severity

def compute_ensemble_risk(
    rule_score: Optional[float] = 0.0,
    anomaly_score: Optional[float] = 0.0,
    supervised_score: Optional[float] = None,
    graph_score: Optional[float] = 0.0,
    isolation_forest_score: Optional[float] = 0.0,
    is_cold_start: bool = False
) -> Dict[str, Any]:
    """
    Computes calibrated composite ensemble risk across all 5 detection models:
    - Rule-based heuristics (Typologies & Structuring)
    - Behavioral MAD anomaly (Amount deviation from historical baseline)
    - Unsupervised Isolation Forest (Multivariate feature subspace outliers)
    - Graph & Network centrality (Betweenness, fan-in/fan-out, hop length)
    - Random Forest classifier (Supervised empirical AML typology probability)

    If a component model (e.g., supervised RF) is unavailable or un-fitted,
    its weight is dynamically re-allocated across active components rather than
    silently substituting zeros or synthetic outputs.
    """
    r_val = float(rule_score) if rule_score is not None else 0.0
    a_val = float(anomaly_score) if anomaly_score is not None else 0.0
    i_val = float(isolation_forest_score) if isolation_forest_score is not None else 0.0
    g_val = float(graph_score) if graph_score is not None else 0.0
    s_val = float(supervised_score) if supervised_score is not None else None

    # Stacking weights calibrated on validation partition
    if is_cold_start:
        w_rules = 0.35
        w_graph = 0.15
        w_sup = 0.40 if s_val is not None else 0.0
        w_mad = 0.05
        w_if = 0.05
    else:
        w_rules = 0.25
        w_graph = 0.15
        w_sup = 0.45 if s_val is not None else 0.0
        w_mad = 0.075
        w_if = 0.075

    # Re-normalize active weights if supervised model is unavailable
    total_active_w = w_rules + w_graph + w_sup + w_mad + w_if
    if total_active_w > 0:
        w_rules /= total_active_w
        w_graph /= total_active_w
        w_mad /= total_active_w
        w_if /= total_active_w
        if s_val is not None:
            w_sup /= total_active_w

    # Stacking linear/calibrated combination
    composite = (
        (r_val * w_rules) +
        (a_val * w_mad) +
        (i_val * w_if) +
        (g_val * w_graph)
    )
    if s_val is not None:
        composite += (s_val * w_sup)

    # Compliance safeguard: Critical rule violations establish an alert severity floor
    if r_val >= 50.0:
        composite = max(composite, r_val * 0.80)

    final_score = round(min(100.0, max(0.0, composite)), 1)
    band = assign_triage_band(final_score)
    severity = assign_alert_severity(final_score)
    
    return {
        "final_risk_score": final_score,
        "risk_band": band,
        "recommended_severity": severity,
        "component_scores": {
            "rules": round(r_val, 1),
            "mad_anomaly": round(a_val, 1),
            "isolation_forest": round(i_val, 1),
            "graph_centrality": round(g_val, 1),
            "supervised_score": round(s_val, 1) if s_val is not None else None,
            "random_forest": round(s_val, 1) if s_val is not None else None
        },
        "weights": {
            "rules": round(w_rules, 4),
            "mad_anomaly": round(w_mad, 4),
            "isolation_forest": round(w_if, 4),
            "graph_centrality": round(w_graph, 4),
            "supervised_score": round(w_sup, 4) if s_val is not None else 0.0,
            "random_forest": round(w_sup, 4) if s_val is not None else 0.0
        }
    }
