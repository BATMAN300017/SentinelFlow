from typing import Dict, Any, List
from app.detection.calibration import assign_triage_band, assign_alert_severity

def compute_ensemble_risk(
    rule_score: float,
    anomaly_score: float,
    supervised_score: float,
    graph_score: float,
    isolation_forest_score: float = 0.0,
    is_cold_start: bool = False
) -> Dict[str, Any]:
    """
    Computes calibrated composite ensemble risk across all 5 detection models:
    - Rule-based heuristics
    - Behavioral MAD anomaly
    - Unsupervised Isolation Forest
    - Graph & Network centrality
    - Random Forest classifier
    """
    if is_cold_start:
        w_rules = 0.35
        w_graph = 0.30
        w_rf = 0.25
        w_mad = 0.05
        w_if = 0.05
    else:
        w_rules = 0.30
        w_graph = 0.20
        w_rf = 0.20
        w_mad = 0.15
        w_if = 0.15
    
    # Composite calculation
    composite = (
        (float(rule_score) * w_rules) +
        (float(anomaly_score) * w_mad) +
        (float(isolation_forest_score) * w_if) +
        (float(graph_score) * w_graph) +
        (float(supervised_score) * w_rf)
    )

    # Compliance safeguard: Critical rule violations establish an alert severity floor
    if float(rule_score) >= 50.0:
        composite = max(composite, float(rule_score) * 0.60)
    
    final_score = round(min(100.0, max(0.0, composite)), 1)
    band = assign_triage_band(final_score)
    severity = assign_alert_severity(final_score)
    
    return {
        "final_risk_score": final_score,
        "risk_band": band,
        "recommended_severity": severity,
        "component_scores": {
            "rules": round(float(rule_score), 1),
            "mad_anomaly": round(float(anomaly_score), 1),
            "isolation_forest": round(float(isolation_forest_score), 1),
            "graph_centrality": round(float(graph_score), 1),
            "random_forest": round(float(supervised_score), 1)
        },
        "weights": {
            "rules": w_rules,
            "mad_anomaly": w_mad,
            "isolation_forest": w_if,
            "graph_centrality": w_graph,
            "random_forest": w_rf
        }
    }
