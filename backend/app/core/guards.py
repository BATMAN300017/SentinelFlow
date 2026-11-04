import os
import logging
import urllib.parse

logger = logging.getLogger("sentinelflow.guards")

PROD_ENV_NAMES = {"production", "prod", "live"}
PROD_HOST_KEYWORDS = {
    "supabase.co", "supabase.com", "pooler.supabase.com",
    "rds.amazonaws.com", "cloudsql", "googleapis.com",
    "render.com", "neon.tech", "cockroachlabs.cloud",
    "azure.com", "fly.dev", "herokuapp.com"
}
LOCAL_SAFE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "testdb", "mock"}

def check_demo_environment_guard(operation_name: str = "Demo fixture seeding") -> None:
    """
    Enforces strict, unconditional production safety guards.
    1. Production environments (ENVIRONMENT, APP_ENV, NODE_ENV, ENV, SENTINELFLOW_ENV, STAGE, TARGET_ENV)
       strictly and unconditionally reject demo seeding, demo simulation, and demo database resets.
       ALLOW_DEMO_SEEDING=true can NEVER override a production environment.
    2. Any attempt to target a production or remote database (DATABASE_URL, SUPABASE_URL, PGHOST, etc.)
       is strictly rejected regardless of overrides. Database safety does not rely solely on substring checks.
    3. Demo fixtures are only permitted in an explicit non-production environment (e.g. 'test', 'demo', 'development')
       targeting a verified local/test non-production storage (e.g., local SQLite).
    """
    # 1. Unconditional production environment rejection
    env_keys = ["ENVIRONMENT", "APP_ENV", "NODE_ENV", "ENV", "SENTINELFLOW_ENV", "STAGE", "TARGET_ENV"]
    for k in env_keys:
        val = os.environ.get(k, "").strip().lower()
        if val in PROD_ENV_NAMES or val.startswith("prod"):
            raise PermissionError(
                f"{operation_name} is strictly prohibited in production environments ({k}='{val}'). "
                "ALLOW_DEMO_SEEDING cannot override production environment."
            )

    # 2. Database target safety checks (independent of overrides)
    db_urls = [
        os.environ.get("DATABASE_URL", "").strip(),
        os.environ.get("SUPABASE_URL", "").strip(),
        os.environ.get("POSTGRES_URL", "").strip()
    ]

    for url_str in db_urls:
        if not url_str:
            continue
        url_lower = url_str.lower()
        
        # Keyword checks for prod/live in database URL
        if "prod" in url_lower or "live" in url_lower:
            raise PermissionError(
                f"{operation_name} is strictly prohibited: TARGET DATABASE IS PRODUCTION. "
                "Demo seeding cannot be executed against a production database target under any override."
            )

        # Parse URL host for remote/cloud infrastructure
        try:
            parsed = urllib.parse.urlparse(url_lower)
            # Local SQLite files and in-memory test databases are safe
            if parsed.scheme.startswith("sqlite") or ":memory:" in url_lower:
                continue

            hostname = parsed.hostname
            if hostname:
                # Reject known cloud database providers
                if any(provider in hostname for provider in PROD_HOST_KEYWORDS):
                    raise PermissionError(
                        f"{operation_name} is strictly prohibited: REMOTE CLOUD DATABASE TARGET ({hostname}). "
                        "Demo seeding cannot be executed against remote or cloud database targets under any override."
                    )
                # Reject non-local remote hosts
                if hostname not in LOCAL_SAFE_HOSTS:
                    raise PermissionError(
                        f"{operation_name} is strictly prohibited: REMOTE DATABASE TARGET ({hostname}). "
                        "Demo seeding is only permitted on verified local/test databases."
                    )
        except Exception as e:
            if isinstance(e, PermissionError):
                raise
            raise PermissionError(
                f"{operation_name} is strictly prohibited: UNVERIFIABLE DATABASE TARGET. Error: {e}"
            )

    # Check PGHOST and PGDATABASE explicitly
    pghost = os.environ.get("PGHOST", "").strip().lower()
    if pghost and pghost not in LOCAL_SAFE_HOSTS:
        raise PermissionError(
            f"{operation_name} is strictly prohibited: REMOTE PGHOST ({pghost}). "
            "Demo seeding is only permitted on verified local/test databases."
        )

    pgdb = os.environ.get("PGDATABASE", "").strip().lower()
    if "prod" in pgdb or "live" in pgdb:
        raise PermissionError(
            f"{operation_name} is strictly prohibited: PRODUCTION DATABASE NAME ({pgdb}). "
            "Demo seeding cannot target production databases."
        )
