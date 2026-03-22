import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "backend" / "output" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = 0.1

# ── News API ──────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_MAX_ARTICLES = 5

# ── SEC EDGAR ─────────────────────────────────────────────────────────────────
EDGAR_USER_AGENT = "FinSight dhananjay.ism24@gmail.com"
EDGAR_MAX_FILINGS = 2        # how many recent filings to fetch per company

# ── PostgreSQL ────────────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "finsight")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ── API ───────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# ── Agent config ──────────────────────────────────────────────────────────────
MAX_RETRIES = 3              # agent retry attempts on tool failure
MEMO_MAX_TOKENS = 2000       # max tokens for generated memo narrative


# ── Validation ────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY is missing from .env")
    if not NEWS_API_KEY:
        errors.append("NEWS_API_KEY is missing from .env")
    if errors:
        raise EnvironmentError("\n".join(errors))
    print("✅ Config validated successfully")
    print(f"   LLM      : {LLM_MODEL}")
    print(f"   Database : {DB_NAME} @ {DB_HOST}:{DB_PORT}")
    print(f"   Output   : {OUTPUT_DIR}")


if __name__ == "__main__":
    validate_config()