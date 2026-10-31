import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("Testing GET /api/v1/learning/summary...")
    res = client.get("/api/v1/learning/summary")
    assert res.status_code == 200, f"Summary failed: {res.text}"
    summary = res.json()
    print("Summary:", summary)
    assert summary["total_transactions_scored"] >= 482000
    assert summary["active_production_models_count"] == 6

    print("\nTesting GET /api/v1/learning/performance...")
    res = client.get("/api/v1/learning/performance")
    assert res.status_code == 200, f"Performance failed: {res.text}"
    perf = res.json()
    print("Overall metrics:", perf["overall"]["metrics"])
    print("Overall confusion matrix:", perf["overall"]["confusion_matrix"])
    print("Dataset wise keys:", list(perf["dataset_wise"].keys()))
    assert perf["dataset_wise"]["SAML_D"]["status"] == "EVALUATED"
    assert perf["dataset_wise"]["INDIA_SIMULATOR"]["status"] == "NOT EVALUATED"
    assert perf["dataset_wise"]["AML_SIM"]["status"] == "NOT EVALUATED"
    assert perf["dataset_wise"]["PAYSIM"]["status"] == "NOT EVALUATED"

    print("\nTesting GET /api/v1/learning/comparison...")
    res = client.get("/api/v1/learning/comparison")
    assert res.status_code == 200
    comp = res.json()
    print("Compared models count:", len(comp["model_comparison"]))
    assert len(comp["model_comparison"]) >= 5

    print("\nTesting GET /api/v1/learning/feedback...")
    res = client.get("/api/v1/learning/feedback?page=1&page_size=10")
    assert res.status_code == 200
    fb = res.json()
    print(f"Feedback total: {fb['total']}, items: {len(fb['items'])}")
    assert fb["total"] >= 4

    print("\nTesting POST /api/v1/learning/feedback...")
    test_fb_payload = {
        "alert_id": "ALT-REAL-0001",
        "transaction_id": "TXN-SAML-000317",
        "account_id": "7401327478",
        "investigator_decision": "CONFIRMED_FRAUD",
        "explanation": "Structured pass-through transfers with immediate ATM cash-out.",
        "supporting_evidence": "Audit logs, counterparty analysis, velocity spikes.",
        "reviewer_id": "USR-TEST-01",
        "reviewer_name": "Test Investigator"
    }
    res_sub = client.post("/api/v1/learning/feedback", json=test_fb_payload)
    assert res_sub.status_code == 200, f"Feedback submit failed: {res_sub.text}"
    fb_sub_data = res_sub.json()
    print("Created feedback:", fb_sub_data)
    assert fb_sub_data["success"] is True
    assert fb_sub_data["validation_status"] == "PENDING_VALIDATION"
    fb_id = fb_sub_data["feedback_id"]

    print("\nTesting POST /api/v1/learning/validate-feedback...")
    val_payload = {
        "feedback_id": fb_id,
        "status": "APPROVED_FOR_TRAINING",
        "training_label": 1,
        "validation_notes": "Evidence verified against bank statements."
    }
    res_val = client.post("/api/v1/learning/validate-feedback", json=val_payload)
    assert res_val.status_code == 200, f"Feedback validation failed: {res_val.text}"
    val_data = res_val.json()
    print("Validation response:", val_data)
    assert val_data["validation_status"] == "APPROVED"
    assert val_data["is_eligible_for_training"] is True

    print("\nTesting GET /api/v1/learning/history...")
    res_hist = client.get("/api/v1/learning/history")
    assert res_hist.status_code == 200
    hist = res_hist.json()
    print("Active version in history:", hist["active_version"])
    print("Training runs count:", len(hist["training_runs"]))

    print("\nTesting GET /api/v1/learning/monitoring...")
    res_mon = client.get("/api/v1/learning/monitoring")
    assert res_mon.status_code == 200
    mon = res_mon.json()
    print("Monitoring transactions scored:", mon["transactions_scored"])
    print("Risk score counts:", mon["risk_score_distribution"]["counts"])
    print("Risk score %:", mon["risk_score_distribution"]["percentages"])
    assert mon["transactions_scored"] >= 482000

    print("\nTesting Controlled Pipeline: prepare-dataset -> train -> evaluate -> approve -> activate -> rollback...")
    # Prepare
    prep_res = client.post("/api/v1/learning/prepare-dataset")
    assert prep_res.status_code == 200
    prep_data = prep_res.json()
    print("Dataset prep sample count:", prep_data["sample_count"])

    # Train
    train_res = client.post("/api/v1/learning/train", json={"trainer_name": "Test ML Architect"})
    assert train_res.status_code == 200
    train_data = train_res.json()
    print("Training response:", train_data)
    assert train_data["success"] is True
    cand_version = train_data["candidate_version"]

    # Evaluate
    eval_res = client.post("/api/v1/learning/evaluate", json={"model_version": cand_version})
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    print("Candidate evaluation response:", eval_data)
    assert eval_data["approval_status"] == "AWAITING_APPROVAL"

    # Approve
    app_res = client.post(f"/api/v1/learning/models/{cand_version}/approve", json={"rationale": "Test sign-off"})
    assert app_res.status_code == 200
    app_data = app_res.json()
    print("Approval response:", app_data)
    assert app_data["approval_status"] == "APPROVED"

    # Activate
    act_res = client.post(f"/api/v1/learning/models/{cand_version}/activate")
    assert act_res.status_code == 200
    act_data = act_res.json()
    print("Activation response:", act_data)
    assert act_data["active_version"] == cand_version

    # Rollback to baseline v1.0.0
    rb_res = client.post("/api/v1/learning/rollback", json={"target_version": "v1.0.0"})
    assert rb_res.status_code == 200
    rb_data = rb_res.json()
    print("Rollback response:", rb_data)
    assert rb_data["active_version"] == "v1.0.0"

    print("\nALL BACKEND MODEL INTELLIGENCE ENDPOINTS PASSED WITH FLYING COLORS!")

if __name__ == "__main__":
    test_endpoints()
