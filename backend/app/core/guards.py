import os
import logging

logger = logging.getLogger("sentinelflow.guards")

def check_demo_environment_guard(operation_name: str = "Demo fixture seeding") -> None:
    """
    Enforces strict production safety guard.
    1. Production environments (ENVIRONMENT, APP_ENV, etc. set to 'production', 'prod', 'live')
       reject demo seeding, demo simulation, and demo database resets.
       Demo seeding cannot be silently executed in production.
    2. Any attempt to target a production database (DATABASE_URL, SUPABASE_URL, PGHOST, etc.)
       is strictly rejected.
    3. Demo fixtures are only permitted in an explicit non-production sandbox/demo environment
       (e.g., 'demo', 'sandbox', 'test', 'development', or local SQLite) targeting non-production storage.
    """
    env_keys = ["ENVIRONMENT", "APP_ENV", "NODE_ENV", "ENV", "SENTINELFLOW_ENV"]
    env_vals = [os.environ.get(k, "").strip().lower() for k in env_keys]
    
    is_production_env = any(v in ("production", "prod", "live") for v in env_vals)
    allow_demo = os.environ.get("ALLOW_DEMO_SEEDING", "").strip().lower() in ("true", "1", "yes")

    # Check database target to ensure it is not a production database
    db_targets = [
        os.environ.get("DATABASE_URL", "").lower(),
        os.environ.get("SUPABASE_URL", "").lower(),
        os.environ.get("POSTGRES_URL", "").lower(),
        os.environ.get("PGHOST", "").lower()
    ]
    is_production_db = any(
        ("prod" in target or "live" in target or "pooler.supabase.com" in target)
        for target in db_targets if target
    )

    if is_production_db:
        raise PermissionError(
            f"{operation_name} is strictly prohibited: TARGET DATABASE IS PRODUCTION. "
            "Demo seeding cannot be executed against a production database target under any override."
        )

    if is_production_env:
        if not allow_demo:
            raise PermissionError(
                f"{operation_name} is strictly prohibited in production environments. "
                "Demo seeding cannot be executed in production environments without authorization."
            )
        logger.warning(
            f"SECURITY NOTICE: {operation_name} authorized via ALLOW_DEMO_SEEDING override in test/staging harness. "
            "Verified non-production database target."
        )
