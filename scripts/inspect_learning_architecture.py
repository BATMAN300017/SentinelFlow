import os
import sys

# Ensure backend is in path
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import get_db_connection

def inspect():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
        tables = [r["table_name"] if isinstance(r, dict) or hasattr(r, "keys") else r[0] for r in cur.fetchall()]
        print("Existing Public Tables:", tables)
        
        # Check model_versions
        if "model_versions" in tables:
            cur.execute("SELECT * FROM model_versions LIMIT 5;")
            print("\nmodel_versions sample:")
            for row in cur.fetchall():
                print(dict(row))
        
        # Check analyst_feedback / investigator_feedback
        for fb_table in ["analyst_feedback", "investigator_feedback"]:
            if fb_table in tables:
                cur.execute(f"SELECT COUNT(*) as c FROM {fb_table};")
                cnt = cur.fetchone()
                print(f"\n{fb_table} count:", cnt["c"] if hasattr(cnt, "keys") else cnt[0])
                cur.execute(f"SELECT * FROM {fb_table} LIMIT 2;")
                for row in cur.fetchall():
                    print(dict(row))

        # Check model_promotion_policy
        if "model_promotion_policy" in tables:
            cur.execute("SELECT * FROM model_promotion_policy;")
            for row in cur.fetchall():
                print("Policy:", dict(row))

if __name__ == "__main__":
    inspect()
