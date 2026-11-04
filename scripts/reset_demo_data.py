import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import transaction_scope
from app.core.guards import check_demo_environment_guard

def reset_demo_database():
    check_demo_environment_guard("Demo database reset")
    print("Safely wiping demo simulation transactions and alerts...")
    with transaction_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM investigation_events")
        cursor.execute("DELETE FROM investigation_tasks")
        cursor.execute("DELETE FROM investigation_notes")
        cursor.execute("DELETE FROM evidence_items")
        cursor.execute("DELETE FROM investigation_alerts")
        cursor.execute("DELETE FROM investigations")
        cursor.execute("DELETE FROM alert_findings")
        cursor.execute("DELETE FROM alerts")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM analyst_feedback")
        cursor.execute("DELETE FROM audit_events")
    print("Simulation tables reset. Demo users, accounts, and rules preserved.")

if __name__ == "__main__":
    reset_demo_database()
