import os
import sys

sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import get_db_connection
from app.evaluation.evaluator import IndependentEvaluator

def test_eval():
    with get_db_connection() as conn:
        print("Testing SAML_D evaluation...")
        res_saml = IndependentEvaluator.evaluate_transaction_level(conn, "SAML_D")
        print("SAML_D metrics:", res_saml.get("metrics"))
        print("SAML_D confusion:", res_saml.get("confusion_matrix"))
        print("SAML_D total evaluated:", res_saml.get("total_evaluated_samples"))

        print("\nTesting NFPC mule evaluation...")
        res_nfpc = IndependentEvaluator.evaluate_account_level(conn, "NFPC_MULE")
        print("NFPC metrics:", res_nfpc.get("metrics"))
        print("NFPC confusion:", res_nfpc.get("confusion_matrix"))
        print("NFPC total evaluated accounts:", res_nfpc.get("total_evaluated_accounts"))

if __name__ == "__main__":
    test_eval()
