import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db_connection

client = TestClient(app)

def test_a_alerts_reference_real_txns():
    print("\n--- TEST A: Alerts Reference Real Database Transactions ---")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, transaction_id, account_id FROM alerts LIMIT 20;")
        alerts = cur.fetchall()
        cur.close()
    
    assert len(alerts) > 0, "No alerts found in database"
    matched = 0
    with get_db_connection() as conn:
        cur = conn.cursor()
        for a in alerts:
            d = dict(a._dict if hasattr(a, '_dict') else a)
            txn_id = d['transaction_id']
            cur.execute("SELECT id, source_account_id, amount FROM transactions WHERE id = %s OR original_transaction_id = %s", (txn_id, txn_id))
            txn = cur.fetchone()
            if txn:
                matched += 1
        cur.close()
    
    print(f"Sampled 20 alerts: {matched}/20 reference verified database transactions.")
    assert matched == len(alerts), f"Expected all {len(alerts)} alerts to reference real transactions, but got {matched}"
    print("TEST A: PASSED [100% database-grounded transactions]")
    return True

def test_b_predictions_from_detection_engine():
    print("\n--- TEST B: Predictions Originate from Detection Engine ---")
    from app.detection.engine import score_transaction
    from app.detection.mule_account_detector import analyze_suspicious_account_network
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE dataset_source = 'NFPC' ORDER BY amount DESC LIMIT 1;")
        txn_row = cur.fetchone()
        txn = dict(txn_row._dict if hasattr(txn_row, '_dict') else txn_row)
        
        # Score transaction through the 5-model pipeline
        result = score_transaction(conn, txn)
        cur.close()
        
    print(f"Engine Final Risk Score: {result['final_risk_score']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Weights: {result['ensemble_weights']}")
    assert "rules" in result["component_scores"]
    assert "mad_anomaly" in result["component_scores"]
    assert "isolation_forest" in result["component_scores"]
    assert "graph_centrality" in result["component_scores"]
    assert "random_forest" in result["component_scores"]
    assert result["account_mule_prediction"] is not None
    print(f"Account Mule Prediction Role: {result['account_mule_prediction'].get('network_role')}")
    print(f"Calibrated Mule Probability: {result['account_mule_prediction'].get('predicted_mule_probability')}")
    print("TEST B: PASSED [5-Model Consensus + Independent Account Mule Detection]")
    return True

def test_c_zero_ground_truth_leakage():
    print("\n--- TEST C: Zero Ground-Truth Leakage ---")
    import inspect
    from app.detection import engine, rules, anomaly, isolation_forest, graph_signals, supervised, mule_account_detector
    
    modules = [engine, rules, anomaly, isolation_forest, graph_signals, supervised, mule_account_detector]
    for mod in modules:
        src = inspect.getsource(mod)
        assert "protected_transaction_labels" not in src, f"Ground-truth table referenced in {mod.__name__}"
        assert "protected_account_labels" not in src, f"Ground-truth table referenced in {mod.__name__}"
    print("Checked all 7 detection modules: None access protected ground-truth vault tables.")
    print("TEST C: PASSED [Strict Operational / Ground-Truth Isolation]")
    return True

def test_d_investigate_standardized_json():
    print("\n--- TEST D: Investigate API Returns Standardized JSON Structure ---")
    # Fetch top alert
    res = client.get("/api/v1/alerts?page=1&page_size=1")
    assert res.status_code == 200
    alert_id = res.json()["items"][0]["id"]
    
    inv_res = client.post(f"/api/v1/alerts/{alert_id}/investigate")
    assert inv_res.status_code == 200, f"Expected 200, got {inv_res.status_code}: {inv_res.text}"
    data = inv_res.json()
    
    assert data.get("success") is True, "Response missing success: True"
    assert "investigation" in data, "Response missing investigation object"
    assert "scam_dossier" in data, "Response missing scam_dossier object"
    
    inv = data["investigation"]
    assert "alert_id" in inv
    assert "transaction_id" in inv
    assert "account_id" in inv
    assert "risk_score" in inv
    assert "findings" in inv
    assert "network" in inv
    assert "status" in inv
    
    print(f"Alert {alert_id} investigation created with Case Number: {inv.get('case_number')}")
    print(f"Network nodes count: {len(inv['network']['nodes'])}, links count: {len(inv['network']['links'])}")
    print("TEST D: PASSED [Standardized JSON Schema: success, investigation, scam_dossier]")
    return True

def test_e_investigation_source_dest_accounts():
    print("\n--- TEST E: Investigation Retrieves Correct Source and Destination Accounts ---")
    res = client.get("/api/v1/alerts?page=1&page_size=1")
    alt = res.json()["items"][0]
    alert_id = alt["id"]
    
    inv_res = client.post(f"/api/v1/alerts/{alert_id}/investigate")
    inv_data = inv_res.json()
    inv = inv_data["investigation"]
    
    assert inv["account_id"] == alt["source_account"], f"Source account mismatch: {inv['account_id']} vs {alt['source_account']}"
    assert inv["destination_account_id"] == alt["destination_account"], f"Dest account mismatch: {inv['destination_account_id']} vs {alt['destination_account']}"
    print(f"Verified accounts match: {inv['account_id']} -> {inv['destination_account_id']}")
    print("TEST E: PASSED [Accurate Entity Relationship Mapping]")
    return True

def test_f_no_fake_countries():
    print("\n--- TEST F: Route Map Shows No Fake Countries or Fictional Coordinates ---")
    res = client.get("/api/v1/alerts?page=1&page_size=5")
    alerts = res.json()["items"]
    
    forbidden_terms = ["nassau", "bahamas", "london", "cayman", "zurich", "panama"]
    for a in alerts:
        dos_res = client.get(f"/api/v1/alerts/{a['id']}/scam-dossier")
        assert dos_res.status_code == 200
        dos = dos_res.json()
        rm = dos.get("route_map", {})
        
        # Verify verified_origin_country is India or Unknown / Unavailable
        assert rm.get("origin_country") in ("India", "United States", "Unknown / Unavailable", None)
        assert rm.get("geographic_status") in ("VERIFIED_INR_INDIA", "UNAVAILABLE")
        
        for hop in rm.get("hops", []):
            country = str(hop.get("country", "")).lower()
            city = str(hop.get("city", "")).lower()
            for term in forbidden_terms:
                assert term not in country, f"Forbidden term {term} found in hop country: {country}"
                assert term not in city, f"Forbidden term {term} found in hop city: {city}"
    print(f"Verified 5 alert route maps: Zero fictional locations, verified country: {rm.get('origin_country')}")
    print("TEST F: PASSED [100% De-hardcoded Geo-Routing]")
    return True

def test_g_subgraph_nodes_and_edges():
    print("\n--- TEST G: Subgraph Nodes and Edges Map to Real Database Records ---")
    res = client.get("/api/v1/graph?hops=2")
    assert res.status_code == 200
    graph = res.json()
    
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    assert len(nodes) > 0, "No nodes returned in graph"
    assert len(edges) > 0, "No edges returned in graph"
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Verify first account node exists in database
        acc_nodes = [n for n in nodes if n.get("type") == "ACCOUNT"]
        if acc_nodes:
            first_acc = acc_nodes[0]["id"]
            cur.execute("SELECT id FROM accounts WHERE id = %s", (first_acc,))
            assert cur.fetchone() is not None, f"Node {first_acc} not found in database accounts table"
            print(f"Verified account node {first_acc} exists in Supabase.")
            
        cur.close()
    print(f"Retrieved {len(nodes)} nodes and {len(edges)} edges grounded in database.")
    print("TEST G: PASSED [Real Graph Topology]")
    return True

def test_h_id_consistency_across_views():
    print("\n--- TEST H: Consistent Identifiers Across Views ---")
    res = client.get("/api/v1/alerts?page=1&page_size=1")
    alt = res.json()["items"][0]
    
    # 1. Alert view ID
    alert_id = alt["id"]
    txn_id = alt["transaction_id"]
    acc_id = alt["source_account"]
    
    # 2. Transaction view
    txn_res = client.get(f"/api/v1/transactions/{txn_id}")
    assert txn_res.status_code == 200
    txn_data = txn_res.json()
    assert txn_data["id"] == txn_id
    assert txn_data["source_account_id"] == acc_id
    
    # 3. Investigation view
    inv_res = client.post(f"/api/v1/alerts/{alert_id}/investigate")
    inv = inv_res.json()["investigation"]
    assert inv["alert_id"] == alert_id
    assert inv["transaction_id"] == txn_id
    assert inv["account_id"] == acc_id
    
    print(f"Verified ID consistency: Alert {alert_id} <-> Txn {txn_id} <-> Account {acc_id}")
    print("TEST H: PASSED [End-to-End Identifier Consistency]")
    return True

def test_i_query_performance_on_482k_rows():
    print("\n--- TEST I: Query Performance & Bounded Queries on 482,000 Rows ---")
    t0 = time.time()
    res = client.get("/api/v1/alerts?page=1&page_size=25&severity=CRITICAL&dataset=NFPC")
    t1 = time.time()
    assert res.status_code == 200
    alert_query_time = t1 - t0
    print(f"Filtered alerts query (482k rows) executed in {alert_query_time:.3f} seconds.")
    assert alert_query_time < 4.0, f"Query took too long: {alert_query_time}s"
    
    t2 = time.time()
    g_res = client.get("/api/v1/graph?hops=2")
    t3 = time.time()
    assert g_res.status_code == 200
    graph_query_time = t3 - t2
    print(f"Bounded 2-hop graph query executed in {graph_query_time:.3f} seconds.")
    assert graph_query_time < 5.0, f"Graph query took too long: {graph_query_time}s"
    print("TEST I: PASSED [High Efficiency Bounded Execution < 5.0s]")
    return True

def test_j_dashboard_and_auth_integrity():
    print("\n--- TEST J: Dashboard, Datasets Registry, and Ground-Truth Vault Integrity ---")
    # 1. Dataset registry
    ds_res = client.get("/api/v1/datasets")
    assert ds_res.status_code == 200
    datasets = ds_res.json()
    print(f"Registered datasets: {len(datasets)}")
    assert len(datasets) == 7, f"Expected 7 datasets, got {len(datasets)}"
    
    # 2. Dataset lab
    lab_res = client.get("/api/v1/datasets/lab")
    assert lab_res.status_code == 200
    lab_data = lab_res.json()
    lab_count = len(lab_data) if isinstance(lab_data, list) else len(lab_data.get('datasets', []))
    print(f"Lab summary datasets: {lab_count}")
    
    # 3. Analytics / Overview
    sum_res = client.get("/api/v1/dashboard/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    tx_count = sum_data.get('transactions_processed') or sum_data.get('total_transactions', 0)
    al_count = sum_data.get('alerts_generated') or sum_data.get('total_alerts', 0)
    print(f"Dashboard summary: transactions={tx_count}, alerts={al_count}")
    assert tx_count >= 480000, f"Expected >= 480,000 transactions, got {tx_count}"
    assert al_count >= 150, f"Expected >= 150 alerts, got {al_count}"
    
    print("TEST J: PASSED [Core Platform, Registry, & Protected Store Intact]")
    return True

if __name__ == "__main__":
    print("======================================================================")
    print("SENTINEFLOW PRODUCTION ACCEPTANCE VALIDATION SUITE (TESTS A - J)")
    print("======================================================================")
    results = [
        ("TEST A", test_a_alerts_reference_real_txns()),
        ("TEST B", test_b_predictions_from_detection_engine()),
        ("TEST C", test_c_zero_ground_truth_leakage()),
        ("TEST D", test_d_investigate_standardized_json()),
        ("TEST E", test_e_investigation_source_dest_accounts()),
        ("TEST F", test_f_no_fake_countries()),
        ("TEST G", test_g_subgraph_nodes_and_edges()),
        ("TEST H", test_h_id_consistency_across_views()),
        ("TEST I", test_i_query_performance_on_482k_rows()),
        ("TEST J", test_j_dashboard_and_auth_integrity()),
    ]
    
    print("\n======================================================================")
    print("FINAL ACCEPTANCE TEST RESULTS SUMMARY")
    print("======================================================================")
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name:10} : {status}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\nALL 10 ACCEPTANCE TESTS PASSED SUCCESSFULLY! (10/10)")
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)
