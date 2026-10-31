import os
import sys

sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import get_db_connection

def verify_tables():
    with get_db_connection() as conn:
        cur = conn.cursor()
        for t in [
            'model_versions', 'model_training_runs', 'model_evaluations',
            'investigator_feedback', 'feedback_validation', 'model_deployments',
            'model_monitoring_metrics'
        ]:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"Table {t:26} : {cnt} rows")

if __name__ == "__main__":
    verify_tables()
