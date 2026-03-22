import sys
import os
import ssl
import certifi
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import validate_config, API_HOST, API_PORT
from backend.api.routes import router
from backend.db.database import check_connection, init_db


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: validate config + check DB. Shutdown: cleanup."""
    print("\n" + "=" * 55)
    print("  FinSight API — Starting Up")
    print("=" * 55)

    try:
        validate_config()
    except EnvironmentError as e:
        print(f"\n❌ Config error:\n{e}")
        raise

    if check_connection():
        print("✅ Database connected")
    else:
        print("⚠️  Database not connected — check PostgreSQL is running")

    print("✅ FinSight API ready\n")

    yield

    print("\n👋 FinSight API shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FinSight API",
    description="""
    Multi-agent financial research system.

    **3-Agent Pipeline:**
    - **Fetcher Agent** — SEC EDGAR filings + news
    - **Analyst Agent** — investment memo generation via LLM
    - **Critic Agent** — fact-checking + confidence scoring

    **POST /api/v1/analyze** with a ticker to run the full pipeline.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "FinSight API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "analyze": "POST /api/v1/analyze",
        "memos": "/api/v1/memos",
        "examples": "/api/v1/examples"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", API_PORT))
    print(f"\n🚀 Starting FinSight API on http://{API_HOST}:{port}")
    print(f"📖 Docs at http://localhost:{port}/docs\n")
    uvicorn.run(
        "backend.api.main:app",
        host=API_HOST,
        port=port,
        reload=False,
        log_level="info"
    )