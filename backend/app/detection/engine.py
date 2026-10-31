import sqlite3
from typing import Dict, Any, List
from app.detection.features import extract_transaction_features
from app.detection.rules import evaluate_rules
from app.detection.anomaly import calculate_mad_anomaly
from app.detection.isolation_forest import get_isolation_forest_score
from app.detection.graph_signals import evaluate_graph_signals
from app.detection.supervised import predict_supervised_risk
from app.detection.mule_account_detector import analyze_suspicious_account_network
from app.detection.ensemble import compute_ensemble_risk
from app.detection.explainability import generate_risk_explanation

def score_transaction(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Feature extraction
    features = extract_transaction_features(conn, txn)
    
    # 2. Rule evaluation (Rule-based engine)
    triggered_rules = evaluate_rules(conn, txn, features)
    rule_score = min(100.0, sum(r["score_contribution"] for r in triggered_rules))
    
    # 3. Behavioral Anomaly (MAD)
    historical_amounts = features.get("historical_amounts", [])
    is_cold = bool(features.get("is_cold_start", 0))
    anomaly_res = calculate_mad_anomaly(float(txn["amount"]), historical_amounts, is_cold)
    anomaly_score = anomaly_res["score"]
    
    # 4. Unsupervised Isolation Forest Anomaly
    if_res = get_isolation_forest_score(features)
    isolation_forest_score = if_res.get("isolation_forest_score", 0.0)
    
    # 5. Graph / Network Signals
    graph_res = evaluate_graph_signals(conn, txn)
    graph_score = graph_res["graph_score"]
    
    # 6. Supervised Random Forest Model (calibrated mule probability)
    sup_res = predict_supervised_risk(features)
    supervised_score = sup_res["supervised_score"]
    
    # 7. Calibrated Ensemble Risk (All 5 models: Rules, MAD, Isolation Forest, Graph, Random Forest)
    ensemble = compute_ensemble_risk(
        rule_score=rule_score,
        anomaly_score=anomaly_score,
        supervised_score=supervised_score,
        graph_score=graph_score,
        isolation_forest_score=isolation_forest_score
    )
    final_score = ensemble["final_risk_score"]
    
    # 8. Distinct Analytical Output: Suspicious Account / Network Prediction
    account_id = txn.get("source_account_id")
    account_mule_prediction = None
    if account_id:
        try:
            account_mule_prediction = analyze_suspicious_account_network(conn, account_id)
        except Exception as e:
            account_mule_prediction = {
                "account_id": account_id,
                "predicted_mule_probability": 0.05,
                "mule_risk_tier": "LOW",
                "network_role": "STANDARD_OPERATING_ACCOUNT",
                "error": str(e)
            }
    
    # 9. Narrative Explanation
    explanation = generate_risk_explanation(
        txn, features, triggered_rules, anomaly_res, graph_res, sup_res, final_score
    )
    
    return {
        "final_risk_score": final_score,
        "risk_band": ensemble["risk_band"],
        "recommended_severity": ensemble["recommended_severity"],
        "component_scores": ensemble["component_scores"],
        "ensemble_weights": ensemble["weights"],
        "triggered_rules": triggered_rules,
        "behavioral_anomaly": anomaly_res,
        "isolation_forest": if_res,
        "graph_signals": graph_res["signals"],
        "supervised_prediction": sup_res,
        "account_mule_prediction": account_mule_prediction,
        "narrative_explanation": explanation,
        "features": features
    }
