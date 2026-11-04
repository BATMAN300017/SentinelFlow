import numpy as np
from typing import Dict, Any, List

def calculate_mad_anomaly(amount: float, historical_amounts: List[float], is_cold_start: bool) -> Dict[str, Any]:
    if is_cold_start or len(historical_amounts) < 5:
        return {
            "score": 10.0,
            "anomaly_detected": False,
            "confidence": "LOW_HISTORY_CONFIDENCE",
            "median": amount,
            "mad": 0.0,
            "z_score_robust": 0.0,
            "reason": "Insufficient account history for statistical baseline (cold start account)"
        }
        
    arr = np.array(historical_amounts, dtype=float)
    median = float(np.median(arr))
    deviations = np.abs(arr - median)
    mad = float(np.median(deviations))
    
    if mad == 0.0:
        mad = float(np.mean(deviations)) or 1.0 # fallback
        
    # Robust z-score using MAD: 0.6745 * (x - median) / MAD
    robust_z = 0.6745 * (amount - median) / mad
    
    score = 0.0
    detected = False
    reason = "Transaction amount is within normal variance"
    
    if robust_z > 4.5:
        # Avoid false positives on minor retail variation below $1,000
        score = 75.0 if amount >= 1000.0 else 25.0
        detected = amount >= 1000.0
        reason = f"Transaction amount (${amount:,.2f}) significantly deviates from account median (${median:,.2f}, robust z={robust_z:.2f})"
    elif robust_z > 3.0:
        score = 50.0 if amount >= 1000.0 else 20.0
        detected = amount >= 1000.0
        reason = f"Transaction amount (${amount:,.2f}) is noticeably elevated above median (${median:,.2f}, robust z={robust_z:.2f})"
    elif robust_z > 2.0:
        score = 25.0
        reason = f"Transaction amount is slightly above typical range (robust z={robust_z:.2f})"
        
    return {
        "score": min(100.0, score),
        "anomaly_detected": detected,
        "confidence": "HIGH",
        "median": round(median, 2),
        "mad": round(mad, 2),
        "z_score_robust": round(robust_z, 2),
        "reason": reason
    }
