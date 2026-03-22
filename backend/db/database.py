import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import DATABASE_URL


# ── SQLAlchemy setup ──────────────────────────────────────────────────────────

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # test connection before using from pool
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ── Dependency for FastAPI ────────────────────────────────────────────────────

def get_db():
    """
    FastAPI dependency — yields a database session
    and closes it when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Utilities ─────────────────────────────────────────────────────────────────

def init_db():
    """
    Creates all tables and enables pgvector extension.
    Run once on startup via scripts/setup_db.py.
    """
    with engine.connect() as conn:
        # Enable pgvector
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("✅ pgvector extension enabled")

    # Create all tables defined in models.py
    from backend.db.models import Base as ModelBase
    ModelBase.metadata.create_all(bind=engine)
    print("✅ All tables created")


def check_connection() -> bool:
    """Returns True if database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing database connection...\n")

    if check_connection():
        print("✅ Connected to PostgreSQL successfully")
        print(f"   URL: {DATABASE_URL.replace(DATABASE_URL.split(':')[2].split('@')[0], '***')}")
    else:
        print("❌ Could not connect — check your .env and PostgreSQL is running")
        print("   Start PostgreSQL: brew services start postgresql@15")