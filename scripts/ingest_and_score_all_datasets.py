import os
import json
from datetime import datetime, timezone
from app.core.database import get_db_connection
from app.data_ingestion.ibm_aml_adapter import IbmAmlAdapter
from app.data_ingestion.paysim_adapter import PaySimAdapter
from app.data_ingestion.elliptic_adapter import EllipticAdapter
from app.data_ingestion.amlsim_adapter import AmlSimScenarioGenerator
from app.api.v1.datasets import _persist_canonical_records

def ingest_and_score_all():
    print("Starting comprehensive ingestion and scoring for all partial datasets...")
    with get_db_connection() as conn:
        # 1. Ingest full sample of IBM AML (100 rows)
        print("Ingesting IBM AML sample records...")
        ibm_gen = IbmAmlAdapter.parse_records("data/ibm_aml/ibm_aml_sample.csv", max_records=100)
        ibm_txns = list(ibm_gen)
        _persist_canonical_records(conn, ibm_txns, "IBM_AML")
        print(f"IBM AML: Processed and scored {len(ibm_txns)} records.")

        # 2. Ingest full sample of PaySim (100 rows)
        print("Ingesting PaySim sample records...")
        paysim_gen = PaySimAdapter.parse_records("data/paysim/paysim_sample.csv", max_records=100)
        paysim_txns = list(paysim_gen)
        _persist_canonical_records(conn, paysim_txns, "PAYSIM")
        print(f"PaySim: Processed and scored {len(paysim_txns)} records.")

        # 3. Ingest full sample of Elliptic (100 rows)
        print("Ingesting Elliptic sample records...")
        elliptic_gen = EllipticAdapter.parse_records(
            "data/elliptic/elliptic_classes_sample.csv",
            "data/elliptic/elliptic_edgelist_sample.csv",
            max_records=100
        )
        elliptic_txns = list(elliptic_gen)
        _persist_canonical_records(conn, elliptic_txns, "ELLIPTIC")
        print(f"Elliptic: Processed and scored {len(elliptic_txns)} records.")

        # 4. Generate all 4 AMLSim Typologies
        print("Generating and scoring AMLSim scenarios (CYCLE, FAN_OUT, FAN_IN, SCATTER_GATHER)...")
        typologies = ["CYCLE", "FAN_OUT", "FAN_IN", "SCATTER_GATHER"]
        total_amlsim = 0
        for idx, typ in enumerate(typologies):
            res = AmlSimScenarioGenerator.generate_scenario(
                typology=typ,
                num_accounts=6,
                base_amount=45000.0 + idx * 5000.0,
                currency="USD",
                random_seed=100 + idx,
                noise_txns_count=12
            )
            _persist_canonical_records(conn, res["transactions"], "AML_SIM")
            total_amlsim += res["total_transactions"]
        print(f"AMLSim: Generated and scored {total_amlsim} transactions across 4 typologies.")

        # 5. Check and score any previously unscored transactions
        cur = conn.cursor()
        cur.execute("""
            SELECT id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, status, dataset_source, created_at
            FROM transactions
            WHERE (risk_score IS NULL OR risk_score = 0.0)
            AND dataset_source IN ('IBM_AML', 'PAYSIM', 'ELLIPTIC', 'AML_SIM')
            LIMIT 500;
        """)
        unscored = cur.fetchall()
        print(f"Found {len(unscored)} unscored transactions. Updating scores...")
        from app.detection.engine import score_transaction
        for row in unscored:
            r_dict = dict(row)
            try:
                res = score_transaction(conn, {
                    "id": r_dict["id"],
                    "source_account_id": r_dict["source_account_id"],
                    "destination_account_id": r_dict["destination_account_id"],
                    "customer_id": r_dict["customer_id"],
                    "amount": float(r_dict["amount"]),
                    "currency": r_dict.get("currency", "USD"),
                    "transaction_type": r_dict.get("transaction_type", "TRANSFER"),
                    "payment_channel": r_dict.get("payment_channel", "TRANSFER"),
                    "status": r_dict.get("status", "COMPLETED"),
                    "created_at": str(r_dict.get("created_at", ""))
                })
                score = res.get("final_risk_score")
                if score is not None:
                    score = float(score)
                    band = res.get("risk_band", "ROUTINE")
                    cur.execute("UPDATE transactions SET risk_score = ?, risk_band = ? WHERE id = ?;", (score, band, r_dict["id"]))
                else:
                    cur.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED' WHERE id = ?;", (r_dict["id"],))
            except Exception as e:
                cur.execute("UPDATE transactions SET risk_score = NULL, risk_band = 'FAILED' WHERE id = ?;", (r_dict["id"],))
        conn.commit()

        # 6. Update counts in datasets table
        cur.execute("""
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'SAML_D'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'SAML_D') WHERE id = 'ds-saml-aml';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'NFPC'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'NFPC') WHERE id = 'ds-nfpc-mule';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'IBM_AML'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'IBM_AML') WHERE id = 'ds-ibm-aml';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'PAYSIM'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'PAYSIM') WHERE id = 'ds-paysim';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'ELLIPTIC'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'ELLIPTIC') WHERE id = 'ds-elliptic';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'AML_SIM'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'AML_SIM') WHERE id = 'ds-amlsim';
            UPDATE datasets SET imported_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'INDIA_SIMULATOR'), processed_record_count = (SELECT COUNT(*) FROM transactions WHERE transactions.dataset_source = 'INDIA_SIMULATOR') WHERE id = 'ds-india-sim';
        """)
        conn.commit()
        print("Updated datasets record counts in database.")

        # Print final transaction count by dataset
        cur.execute("SELECT dataset_source, COUNT(*) FROM transactions GROUP BY dataset_source ORDER BY COUNT(*) DESC;")
        print("\nFinal transaction count by dataset source:")
        for r in cur.fetchall():
            print(" -", dict(r))

        # Print total alerts count by dataset
        cur.execute("""
            SELECT t.dataset_source, COUNT(a.id)
            FROM alerts a
            JOIN transactions t ON a.transaction_id = t.id
            GROUP BY t.dataset_source;
        """)
        print("\nAlerts by dataset source:")
        for r in cur.fetchall():
            print(" -", dict(r))

        cur.execute("SELECT COUNT(*) FROM alerts;")
        print(f"Total system alerts: {cur.fetchone()['count']}")

if __name__ == "__main__":
    ingest_and_score_all()
