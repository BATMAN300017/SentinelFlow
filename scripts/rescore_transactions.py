"""
Offline Transaction Re-Scoring Tool for SentinelFlow AI.

Eliminates pre-remediation leaked or uncalibrated scores by re-evaluating transactions
through the genuine multi-model detection pipeline:
- Rules Engine
- Behavioral MAD Anomaly Detector
- Unsupervised Isolation Forest (empirical account distribution)
- Graph Centrality Engine
- Supervised Random Forest (canonical 9-feature schema)

Safety constraints:
- Defaults to --dry-run (prints proposed updates without writing).
- Requires --execute flag to commit database changes.
- Writes full provenance audit trail for compliance.
"""

import sys
import os
import argparse
from typing import Dict, Any, List

# Ensure backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.core.database import get_db_connection
from app.detection.engine import score_transaction
from app.services.audit_service import record_audit_event
from app.core.logging import logger


def rescore_transactions(
    dataset_source: str = "SAML_D",
    score_filter: str = "leaked_92_5",
    batch_size: int = 100,
    dry_run: bool = True
):
    print("=" * 70)
    print("SENTINELFLOW TRANSACTION RE-SCORING ENGINE")
    print(f"Mode: {'DRY RUN (no database changes)' if dry_run else 'LIVE COMMIT'}")
    print(f"Target Dataset: {dataset_source}")
    print(f"Filter Condition: {score_filter}")
    print("=" * 70)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build query based on filter
        if score_filter == "leaked_92_5":
            query = """
                SELECT id, source_account_id, destination_account_id, customer_id,
                       amount, currency, transaction_type, payment_channel, status, created_at
                FROM transactions
                WHERE dataset_source = ? AND risk_score = 92.5
                ORDER BY created_at ASC;
            """
            params = (dataset_source,)
        elif score_filter == "all_zero_or_null":
            query = """
                SELECT id, source_account_id, destination_account_id, customer_id,
                       amount, currency, transaction_type, payment_channel, status, created_at
                FROM transactions
                WHERE dataset_source = ? AND (risk_score IS NULL OR risk_score = 0.0)
                ORDER BY created_at ASC
                LIMIT 500;
            """
            params = (dataset_source,)
        elif score_filter == "all_unverified":
            query = """
                SELECT id, source_account_id, destination_account_id, customer_id,
                       amount, currency, transaction_type, payment_channel, status, created_at
                FROM transactions
                WHERE dataset_source = ?
                ORDER BY created_at ASC
                LIMIT 500;
            """
            params = (dataset_source,)
        else:
            raise ValueError(f"Unknown score filter: {score_filter}")

        cursor.execute(query, params)
        rows = cursor.fetchall()
        total_found = len(rows)
        print(f"Discovered {total_found} transactions matching filter criteria.\n")

        if total_found == 0:
            print("No transactions requiring re-scoring. Exiting.")
            return

        rescored_count = 0
        updated_count = 0

        for idx, row in enumerate(rows, 1):
            r = dict(row)
            txn_id = r["id"]

            try:
                res = score_transaction(conn, r)
                new_score = res.get("final_risk_score")
                new_band = res.get("risk_band", "ROUTINE")
                rf_score = res.get("component_scores", {}).get("random_forest")
                rules_triggered = [x["rule_code"] for x in res.get("triggered_rules", [])]

                rescored_count += 1
                print(f"[{idx}/{total_found}] {txn_id}: Amount={r['amount']:,.2f} -> "
                      f"New Score={new_score} ({new_band}), RF={rf_score}, Rules={rules_triggered}")

                if not dry_run and new_score is not None:
                    cursor.execute("""
                        UPDATE transactions
                        SET risk_score = ?, risk_band = ?
                        WHERE id = ?;
                    """, (new_score, new_band, txn_id))
                    updated_count += 1

            except Exception as e:
                print(f"[{idx}/{total_found}] {txn_id}: Scoring failed: {e}")

        if not dry_run:
            conn.commit()
            record_audit_event(
                conn,
                actor_id=None,
                actor_name="RESCORING_TOOL",
                action="TRANSACTIONS_RESCORED",
                resource_type="TRANSACTION_BATCH",
                resource_id=f"BATCH-{dataset_source}",
                metadata={
                    "dataset_source": dataset_source,
                    "rescored_count": rescored_count,
                    "updated_count": updated_count,
                    "filter": score_filter
                }
            )
            print(f"\nSuccessfully committed {updated_count} updated transactions to database.")
        else:
            print(f"\nDRY RUN COMPLETE: Evaluated {rescored_count} transactions. No changes written.")


def main():
    parser = argparse.ArgumentParser(description="Re-score transactions with genuine model pipeline.")
    parser.add_argument("--dataset", default="SAML_D", help="Dataset source (e.g., SAML_D, INDIA_SIMULATOR)")
    parser.add_argument("--filter", default="leaked_92_5", choices=["leaked_92_5", "all_zero_or_null", "all_unverified"],
                        help="Filter condition for transactions to re-score")
    parser.add_argument("--execute", action="store_true", help="Commit changes to database (default is dry-run)")
    args = parser.parse_args()

    rescore_transactions(
        dataset_source=args.dataset,
        score_filter=args.filter,
        dry_run=not args.execute
    )


if __name__ == "__main__":
    main()
