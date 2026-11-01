import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api.router import api_router

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelFlow AI — The Self-Directed Fraud Investigation Platform Backend API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware: allow local dev, Render self, and Cloudflare Pages origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://sentinelflow-ljlk.onrender.com",
        "https://sentinelflow.batman3-00017.workers.dev",
        "https://sentinelflow.pages.dev",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Root health check endpoint
@app.get("/health", tags=["Health"])
def root_health():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

# Production Backend API Root (Render)
@app.get("/", tags=["API Info"])
def root_info():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "role": "API backend",
        "canonical_frontend": "https://sentinelflow.batman3-00017.workers.dev",
        "cloudflare_workers_frontend": "https://sentinelflow.batman3-00017.workers.dev",
        "cloudflare_pages_target": "https://sentinelflow.pages.dev",
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1": settings.API_V1_STR,
        "health": "/health",
        "legacy_demo": "/demo"
    }

# Mount static files and preserve legacy HTML only as explicit demo/legacy route
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/demo", include_in_schema=False)
    @app.get("/legacy", include_in_schema=False)
    def serve_legacy_demo():
        index_file = os.path.join(static_dir, "index.html")
        return FileResponse(index_file)

    @app.get("/app", include_in_schema=False)
    def serve_app_redirect():
        return RedirectResponse(url="/demo")

@app.on_event("startup")
def on_startup():
    logger.info("SentinelFlow AI starting up...")
    init_db()
    # Log database transaction count without automatic demo seeding
    try:
        from app.core.database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            logger.info(f"Database contains {count} transactions. Ready.")
    except Exception as e:
        logger.warning(f"Startup database check: {e}")
    logger.info("Database and services initialized successfully.")
