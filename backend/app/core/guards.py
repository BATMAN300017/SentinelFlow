import os

def check_demo_environment_guard(operation_name: str = "Demo fixture seeding") -> None:
    """
    Enforces strict production safety guard.
    Production environments reject demo seeding, demo simulation, and demo database resets by default.
    Only permitted if ALLOW_DEMO_SEEDING is explicitly set to 'true'.
    """
    env_keys = ["ENVIRONMENT", "APP_ENV", "NODE_ENV", "ENV", "SENTINELFLOW_ENV"]
    env_vals = [os.environ.get(k, "").strip().lower() for k in env_keys]
    
    is_production = any(v in ("production", "prod", "live") for v in env_vals)
    allow_demo = os.environ.get("ALLOW_DEMO_SEEDING", "").strip().lower() in ("true", "1", "yes")
    
    if is_production and not allow_demo:
        raise PermissionError(
            f"{operation_name} is strictly prohibited in production environments. "
            "To permit this operation in a dedicated, isolated test/demo sandbox, "
            "set ALLOW_DEMO_SEEDING=true."
        )
