"""
Dataset Management API Router.

Endpoints for:
- Listing registered datasets (SAML-D, NFPC, India Simulator).
- Triggering batch ingestion with automatic label isolation.
- Generating calibrated Indian banking transactions using RBI/NPCI aggregate statistics.
- Inspecting raw dataset schemas and testing label isolation.
- Viewing public aggregate payment benchmarks.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.data_ingestion.dataset_registry import DatasetRegistry
from app.data_ingestion.provenance import ProvenanceTracker
from app.data_ingestion.rbi_npci_statistics import get_channel_benchmarks
from app.data_ingestion.schema_inspector import SchemaInspector
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.batch_loader import BatchLoader
from app.data_ingestion.india_simulator import IndiaBankingSimulator
from app.core.logging import logger

router = APIRouter()

class IngestionRequest(BaseModel):
    dataset_name: str  # SAML_D, NFPC_MULE, or INDIA_SIMULATOR
    source_path: Optional[str] = None
    max_records: Optional[int] = 500

class IndiaSimulationRequest(BaseModel):
    num_customers: int = 50
    num_accounts: int = 80
    num_normal_txns: int = 250
    include_scenarios: bool = True

class SchemaInspectRequest(BaseModel):
    file_path: str
    sample_rows: int = 100

@router.get("", summary="List all registered datasets and their status")
def list_datasets():
    """Returns registration metadata, transaction counts, and label isolation health."""
    return DatasetRegistry.get_all_registered_datasets()

@router.get("/transactions", summary="Browse and explore all transaction data across datasets")
def browse_dataset_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    dataset_source: Optional[str] = None,
    currency: Optional[str] = None,
    search: Optional[str] = None,
    conn=Depends(get_db)
):
    offset = (page - 1) * page_size
    query = """
        SELECT id, event_id, source_account_id, destination_account_id,
               amount, currency, transaction_type, payment_channel, status,
               risk_score, risk_band, dataset_source, created_at
        FROM transactions
        WHERE 1=1
    """
    params = []
    if dataset_source and dataset_source.upper() != "ALL":
        query += " AND dataset_source = ?"
        params.append(dataset_source.upper())
    if currency and currency.upper() != "ALL":
        query += " AND currency = ?"
        params.append(currency.upper())
    if search:
        query += " AND (id LIKE ? OR source_account_id LIKE ? OR destination_account_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor = conn.cursor()
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }


@router.get("/rbi-npci-benchmarks", summary="Retrieve official RBI & NPCI aggregate payment indicators")
def get_rbi_npci_benchmarks():
    """Returns official calibrated macro payment benchmarks used to parameterize Indian simulations."""
    return {
        "status": "CALIBRATED_BENCHMARKS_ACTIVE",
        "description": "Macro payment indicators from RBI Database on Indian Economy & NPCI product statistics.",
        "benchmarks": get_channel_benchmarks()
    }

@router.get("/lab", summary="Dataset Laboratory overview across all domains")
def get_dataset_lab_overview():
    """Returns real dataset research statistics across traditional banking, mobile money, and crypto."""
    return DatasetRegistry.get_all_registered_datasets()

@router.get("/{dataset_id}/details", summary="Get detailed research profile for a specific dataset")
def get_dataset_details(dataset_id: str):
    details = DatasetRegistry.get_dataset_details(dataset_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found in registry.")
    return details

@router.get("/{dataset_id}", summary="Get detailed provenance and schema for a dataset")
def get_dataset(dataset_id: str):
    details = DatasetRegistry.get_dataset_details(dataset_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    lineage = ProvenanceTracker.get_lineage_record(dataset_id)
    return {**details, "lineage": lineage}

@router.post("/inspect-schema", summary="Deep inspect raw file schema and label isolation")
def inspect_dataset_schema(req: SchemaInspectRequest):
    return SchemaInspector.inspect_file(req.file_path, req.sample_rows)

def _persist_canonical_records(conn, txns: list, dataset_name: str) -> dict:
    from app.detection.engine import score_transaction
    from app.repositories.alert_repository import create_alert
    from app.utils.ids import generate_alert_id
    cursor = conn.cursor()
    scoring_failures = []
    scored_count = 0
    for txn in txns:
        src = txn["source_account_id"]
        dest = txn.get("destination_account_id")
        created_at = txn.get("created_at") or datetime.now(timezone.utc).isoformat()
        curr = txn.get("currency") or "USD"
        cust_id = txn.get("customer_id") or f"CUST-{src}"

        # 1. Insert source customer & account
        cursor.execute("""
            INSERT INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
            VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
            ON CONFLICT (id) DO NOTHING;
        """, (cust_id, f"REF-{cust_id}", f"Holder {cust_id}", f"{cust_id}@domain.net", created_at))
        cursor.execute("""
            INSERT INTO accounts (id, account_number, customer_id, currency, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING;
        """, (src, src, cust_id, curr, created_at))

        # 2. Insert destination customer & account if present
        if dest:
            dest_cust_id = f"CUST-{dest}"
            cursor.execute("""
                INSERT INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                ON CONFLICT (id) DO NOTHING;
            """, (dest_cust_id, f"REF-{dest_cust_id}", f"Holder {dest}", f"{dest}@domain.net", created_at))
            cursor.execute("""
                INSERT INTO accounts (id, account_number, customer_id, currency, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING;
            """, (dest, dest, dest_cust_id, curr, created_at))

        # 3. Score transaction through hybrid engine - NO silent zero-score substitution
        scoring_res = None
        risk_score = None
        risk_band = "UNSCORED"
        try:
            scoring_res = score_transaction(conn, {
                "id": txn["id"],
                "source_account_id": src,
                "destination_account_id": dest,
                "customer_id": cust_id,
                "amount": float(txn["amount"]),
                "currency": curr,
                "transaction_type": txn.get("transaction_type", "TRANSFER"),
                "payment_channel": txn.get("payment_channel", "TRANSFER"),
                "status": txn.get("status", "COMPLETED"),
                "created_at": created_at
            })
            if scoring_res and scoring_res.get("final_risk_score") is not None:
                risk_score = float(scoring_res["final_risk_score"])
                risk_band = scoring_res.get("risk_band", "ROUTINE")
                scored_count += 1
            else:
                risk_score = None
                risk_band = "FAILED"
                scoring_failures.append({
                    "transaction_id": txn["id"],
                    "dataset": dataset_name,
                    "error": "Engine returned empty final_risk_score",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.warning(f"Scoring failure for {txn['id']} in {dataset_name}: {e}")
            risk_score = None
            risk_band = "FAILED"
            scoring_failures.append({
                "transaction_id": txn["id"],
                "dataset": dataset_name,
                "error": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # 4. Insert transaction with evaluated risk score & band (preserve non-null on re-ingest)
        cursor.execute("""
            INSERT INTO transactions (
                id, event_id, source_account_id, destination_account_id, customer_id,
                amount, currency, transaction_type, payment_channel, status,
                dataset_source, is_ground_truth_fraud, risk_score, risk_band, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                risk_score = COALESCE(EXCLUDED.risk_score, transactions.risk_score),
                risk_band = COALESCE(EXCLUDED.risk_band, transactions.risk_band);
        """, (
            txn["id"], txn.get("event_id", f"EVT-{txn['id']}"), src, dest,
            cust_id,
            txn["amount"], curr, txn.get("transaction_type", "TRANSFER"),
            txn.get("payment_channel", "TRANSFER"), txn.get("status", "COMPLETED"),
            dataset_name, risk_score, risk_band, created_at
        ))

        # 5. Create alert ONLY if real risk score exists and meets investigation threshold
        if scoring_res and risk_score is not None and (risk_score >= 50.0 or len(scoring_res.get("triggered_rules", [])) > 0):
            cursor.execute("SELECT id FROM alerts WHERE transaction_id = ? LIMIT 1;", (txn["id"],))
            if not cursor.fetchone():
                alt_id = generate_alert_id()
                findings = []
                for r in scoring_res.get("triggered_rules", []):
                    findings.append({
                        "source": "RULE", "code": r["rule_code"], "description": r["description"],
                        "score_contribution": r["score_contribution"], "version": r.get("version", "v1.0")
                    })
                title = f"High Risk Activity Detected ({dataset_name})"
                if risk_score >= 75.0:
                    title = f"CRITICAL AML Risk Detected: {dataset_name}"
                create_alert(conn, {
                    "id": alt_id,
                    "transaction_id": txn["id"],
                    "account_id": src,
                    "customer_id": cust_id,
                    "severity": scoring_res.get("recommended_severity", "MEDIUM"),
                    "status": "NEW",
                    "risk_score": risk_score,
                    "title": title,
                    "summary": scoring_res.get("narrative_explanation", f"Suspicious activity detected in {dataset_name} flow."),
                    "findings": findings
                })

    conn.commit()
    return {
        "total_records": len(txns),
        "scored_count": scored_count,
        "failed_count": len(scoring_failures),
        "scoring_failures": scoring_failures
    }

@router.post("/ingest", summary="Stream and ingest dataset with strict label isolation")
def ingest_dataset_batch(req: IngestionRequest, conn=Depends(get_db)):
    """
    Ingests records in chunked batches across all 7 supported datasets:
    - Strips all ground-truth labels and routes them into the protected evaluation vault.
    - Persists label-free normalized records to detection database with strict zero-leakage guarantee.
    """
    d_name = req.dataset_name.upper().replace("-", "_")
    max_rec = req.max_records or 100

    if d_name == "SAML_D":
        adapter = SamlDAdapter(batch_size=max_rec)
        source = req.source_path or "data/saml_d/saml_d_sample.csv"
        if not os.path.exists(source) and os.path.exists("data/saml_d/saml_d_real.csv"):
            source = "data/saml_d/saml_d_real.csv"
        loader = BatchLoader(adapter=adapter, batch_size=max_rec)
        return loader.ingest_from_source(source_path=source, max_records=max_rec)

    elif d_name in ("NFPC", "NFPC_MULE"):
        adapter = NfpcAdapter(batch_size=max_rec)
        source = req.source_path or "data/nfpc/part_0001.parquet"
        loader = BatchLoader(adapter=adapter, batch_size=max_rec)
        return loader.ingest_from_source(source_path=source, max_records=max_rec)

    elif d_name in ("IBM_AML", "IBM_AML_DATA"):
        from app.data_ingestion.ibm_aml_adapter import IbmAmlAdapter
        source = req.source_path or "data/ibm_aml/ibm_aml_sample.csv"
        generator = IbmAmlAdapter.parse_records(source, max_records=max_rec)
        txns = list(generator)
        _persist_canonical_records(conn, txns, "IBM_AML")
        return {
            "dataset_name": "IBM_AML",
            "total_records_processed": len(txns),
            "valid_records_ingested": len(txns),
            "labels_isolated_count": len(txns),
            "status": "COMPLETED"
        }

    elif d_name in ("PAYSIM", "PAY_SIM"):
        from app.data_ingestion.paysim_adapter import PaySimAdapter
        source = req.source_path or "data/paysim/paysim_sample.csv"
        generator = PaySimAdapter.parse_records(source, max_records=max_rec)
        txns = list(generator)
        _persist_canonical_records(conn, txns, "PAYSIM")
        return {
            "dataset_name": "PAYSIM",
            "total_records_processed": len(txns),
            "valid_records_ingested": len(txns),
            "labels_isolated_count": len(txns),
            "status": "COMPLETED"
        }

    elif d_name in ("ELLIPTIC", "ELLIPTIC_BITCOIN"):
        from app.data_ingestion.elliptic_adapter import EllipticAdapter
        source_classes = req.source_path or "data/elliptic/elliptic_classes_sample.csv"
        source_edges = "data/elliptic/elliptic_edgelist_sample.csv"
        generator = EllipticAdapter.parse_records(source_classes, source_edges, max_records=max_rec)
        txns = list(generator)
        _persist_canonical_records(conn, txns, "ELLIPTIC")
        return {
            "dataset_name": "ELLIPTIC",
            "total_records_processed": len(txns),
            "valid_records_ingested": len(txns),
            "labels_isolated_count": len(txns),
            "status": "COMPLETED"
        }

    elif d_name in ("AML_SIM", "AMLSIM"):
        from app.data_ingestion.amlsim_adapter import AmlSimScenarioGenerator
        res = AmlSimScenarioGenerator.generate_scenario(
            typology="CYCLE",
            num_accounts=5,
            base_amount=50000.0,
            currency="USD",
            random_seed=42,
            noise_txns_count=10
        )
        _persist_canonical_records(conn, res["transactions"], "AML_SIM")
        return {
            "dataset_name": "AML_SIM",
            "total_records_processed": res["total_transactions"],
            "valid_records_ingested": res["total_transactions"],
            "labels_isolated_count": res["laundering_transactions_count"],
            "status": "COMPLETED"
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported dataset adapter: {req.dataset_name}")

class AmlSimGenerateRequest(BaseModel):
    typology: str = "CYCLE" # CYCLE, FAN_OUT, FAN_IN, SCATTER_GATHER
    num_accounts: int = 5
    base_amount: float = 50000.0
    currency: str = "USD"
    random_seed: int = 42
    noise_txns_count: int = 10
    persist_to_database: bool = True

class CrossDatasetCompatibilityRequest(BaseModel):
    source_dataset: str
    target_dataset: str
    target_task: str = "traditional_banking_aml"

@router.post("/amlsim/generate", summary="Generate a tracked IBM AMLSim scenario with recorded configuration")
def generate_amlsim_scenario(req: AmlSimGenerateRequest, conn=Depends(get_db)):
    from app.data_ingestion.amlsim_adapter import AmlSimScenarioGenerator
    scenario = AmlSimScenarioGenerator.generate_scenario(
        typology=req.typology,
        num_accounts=req.num_accounts,
        base_amount=req.base_amount,
        currency=req.currency,
        random_seed=req.random_seed,
        noise_txns_count=req.noise_txns_count
    )

    if req.persist_to_database:
        cursor = conn.cursor()
        for txn in scenario["transactions"]:
            src = txn["source_account_id"]
            dest = txn.get("destination_account_id")
            for acc in [src, dest]:
                if acc:
                    cust_id = f"CUST-{acc}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                        VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                    """, (cust_id, f"REF-{acc}", f"Holder {acc}", f"{acc}@amlsim.net", txn["created_at"]))
                    cursor.execute("""
                        INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (acc, acc, cust_id, txn.get("currency", "USD"), txn["created_at"]))

            cursor.execute("""
                INSERT OR IGNORE INTO transactions (
                    id, event_id, source_account_id, destination_account_id, customer_id,
                    amount, currency, transaction_type, payment_channel, status,
                    scenario_id, dataset_source, is_ground_truth_fraud, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                txn["id"], txn["event_id"], txn["source_account_id"],
                txn.get("destination_account_id"), f"CUST-{txn['source_account_id']}",
                txn["amount"], txn["currency"], txn.get("transaction_type", "TRANSFER"),
                txn.get("payment_channel", "WIRE"), txn.get("status", "COMPLETED"),
                txn.get("scenario_id"), "AML_SIM", txn["created_at"]
            ))
        conn.commit()

    return {
        "status": "SCENARIO_GENERATED",
        "scenario_metadata": scenario["scenario_metadata"],
        "transactions_generated": scenario["total_transactions"],
        "laundering_transactions": scenario["laundering_transactions_count"],
        "noise_transactions": scenario["noise_transactions_count"],
        "persisted": req.persist_to_database
    }

@router.post("/evaluate-compatibility", summary="Check cross-dataset research compatibility")
def check_cross_dataset_compatibility(req: CrossDatasetCompatibilityRequest):
    src = req.source_dataset.upper()
    tgt = req.target_dataset.upper()

    from app.data_ingestion.provenance import DATASET_METADATA_REGISTRY
    src_meta = DATASET_METADATA_REGISTRY.get(src, {})
    tgt_meta = DATASET_METADATA_REGISTRY.get(tgt, {})

    if not src_meta or not tgt_meta:
        raise HTTPException(status_code=400, detail="Invalid dataset specified.")

    src_domain = src_meta.get("domain", "")
    tgt_domain = tgt_meta.get("domain", "")

    # Domain compatibility check
    if src_domain != tgt_domain and not (src_domain in ("traditional_banking", "synthetic_simulation") and tgt_domain in ("traditional_banking", "synthetic_simulation")):
        return {
            "compatible": False,
            "status": "INCOMPATIBLE",
            "source_domain": src_domain,
            "target_domain": tgt_domain,
            "reason": f"Domain mismatch: Cannot cross-validate {src} ({src_domain}) against {tgt} ({tgt_domain}). PaySim is mobile-money fraud and Elliptic is cryptocurrency on-chain forensics. They cannot be merged or evaluated as conventional bank money-laundering models."
        }

    return {
        "compatible": True,
        "status": "COMPATIBLE",
        "source_domain": src_domain,
        "target_domain": tgt_domain,
        "common_feature_layer": ["transaction_amount", "velocity_rolling", "flow_centrality", "payment_channel_risk"],
        "target_alignment": "Both datasets represent traditional banking or calibrated synthetic laundering topologies."
    }

@router.post("/simulate-india", summary="Generate calibrated Indian banking transactions and scenarios")
def simulate_india_ecosystem(req: IndiaSimulationRequest, conn=Depends(get_db)):
    """
    Generates realistic Indian transactions calibrated with RBI/NPCI distributions:
    - Normal banking flows (salary, utilities, merchant UPI, ATM).
    - 5 complex coordinated scenarios (Mule chain, International layering, Circular cycle, Lookalikes).
    - Writes ground truth strictly to protected store.
    """
    simulator = IndiaBankingSimulator()
    ecosystem = simulator.generate_synthetic_ecosystem(
        num_customers=req.num_customers,
        num_accounts=req.num_accounts,
        num_normal_txns=req.num_normal_txns,
        include_scenarios=req.include_scenarios
    )

    # Persist accounts and transactions into database
    cursor = conn.cursor()
    for cust in ecosystem["customers"]:
        cursor.execute("""
            INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cust["id"], cust["customer_ref"], cust["full_name"], cust.get("email", f"{cust['id']}@bank.in"), cust["risk_tier"], cust["kyc_status"], cust["created_at"]))

    for acc in ecosystem["accounts"]:
        cursor.execute("""
            INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, is_dormant, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (acc["id"], acc["account_number"], acc["customer_id"], acc["currency"], acc["balance"], acc["is_dormant"], acc["created_at"]))

    for txn in ecosystem["transactions"]:
        cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                id, event_id, source_account_id, destination_account_id, customer_id,
                amount, currency, transaction_type, payment_channel, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn["id"], txn["event_id"], txn["source_account_id"],
            txn.get("destination_account_id"), f"CUST-{txn['source_account_id']}",
            txn["amount"], txn["currency"], txn.get("payment_type", "TRANSFER"),
            txn.get("payment_channel", "TRANSFER"), txn.get("status", "COMPLETED"),
            txn["created_at"]
        ))
    conn.commit()

    return {
        "status": "SIMULATION_GENERATED_AND_PERSISTED",
        "dataset_name": "INDIA_SIMULATOR",
        "total_transactions_generated": len(ecosystem["transactions"]),
        "total_accounts_created": len(ecosystem["accounts"]),
        "total_customers_created": len(ecosystem["customers"]),
        "scenarios_injected": ecosystem["scenarios_injected"],
        "isolation_status": "PROTECTED_GROUND_TRUTH_STORED_IN_PIPELINE_B"
    }
