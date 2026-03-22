import sys
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[2]))
from backend.db.database import SessionLocal
from backend.db.models import InvestmentMemo, RawFiling, NewsArticle


# ── Investment Memo CRUD ──────────────────────────────────────────────────────

def save_memo(memo_data: dict) -> InvestmentMemo:
    """
    Saves a generated investment memo to the database.
    Called by the crew after all 3 agents complete.
    """
    db: Session = SessionLocal()
    try:
        memo = InvestmentMemo(
            ticker=memo_data.get("ticker", "").upper(),
            company_name=memo_data.get("company_name"),
            summary=memo_data.get("summary"),
            bull_case=memo_data.get("bull_case"),
            bear_case=memo_data.get("bear_case"),
            recommendation=memo_data.get("recommendation"),
            metrics=memo_data.get("metrics"),
            confidence_score=memo_data.get("confidence_score"),
            flagged_claims=memo_data.get("flagged_claims"),
            sources_used=memo_data.get("sources_used"),
            pdf_path=memo_data.get("pdf_path")
        )
        db.add(memo)
        db.commit()
        db.refresh(memo)
        print(f"✅ Memo saved — ticker: {memo.ticker}, id: {memo.id}")
        return memo
    finally:
        db.close()


def get_memo_by_ticker(ticker: str) -> Optional[InvestmentMemo]:
    """
    Returns the most recent memo for a given ticker.
    Used to check if we already have a recent analysis.
    """
    db: Session = SessionLocal()
    try:
        return (
            db.query(InvestmentMemo)
            .filter(InvestmentMemo.ticker == ticker.upper())
            .order_by(InvestmentMemo.created_at.desc())
            .first()
        )
    finally:
        db.close()


def get_all_memos(limit: int = 20) -> list[InvestmentMemo]:
    """Returns the most recent memos across all tickers."""
    db: Session = SessionLocal()
    try:
        return (
            db.query(InvestmentMemo)
            .order_by(InvestmentMemo.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def update_memo_pdf(memo_id: str, pdf_path: str) -> None:
    """Updates the PDF path after generation."""
    db: Session = SessionLocal()
    try:
        memo = db.query(InvestmentMemo).filter(
            InvestmentMemo.id == memo_id
        ).first()
        if memo:
            memo.pdf_path = pdf_path
            db.commit()
    finally:
        db.close()


# ── Raw Filing CRUD ───────────────────────────────────────────────────────────

def save_filing(ticker: str, filing_type: str, content: str,
                filing_date: str = None, url: str = None) -> RawFiling:
    """Saves a raw SEC filing to the database."""
    db: Session = SessionLocal()
    try:
        filing = RawFiling(
            ticker=ticker.upper(),
            filing_type=filing_type,
            filing_date=filing_date,
            content=content,
            url=url
        )
        db.add(filing)
        db.commit()
        db.refresh(filing)
        return filing
    finally:
        db.close()


def get_filings(ticker: str, filing_type: str = None) -> list[RawFiling]:
    """Returns cached filings for a ticker, optionally filtered by type."""
    db: Session = SessionLocal()
    try:
        query = db.query(RawFiling).filter(
            RawFiling.ticker == ticker.upper()
        )
        if filing_type:
            query = query.filter(RawFiling.filing_type == filing_type)
        return query.order_by(RawFiling.fetched_at.desc()).all()
    finally:
        db.close()


# ── News Article CRUD ─────────────────────────────────────────────────────────

def save_articles(ticker: str, articles: list[dict]) -> int:
    """Saves a batch of news articles. Returns count saved."""
    db: Session = SessionLocal()
    try:
        saved = 0
        for article in articles:
            news = NewsArticle(
                ticker=ticker.upper(),
                title=article.get("title"),
                description=article.get("description"),
                content=article.get("content"),
                source=article.get("source", {}).get("name") if isinstance(
                    article.get("source"), dict) else article.get("source"),
                url=article.get("url"),
                published_at=article.get("publishedAt") or article.get("published_at")
            )
            db.add(news)
            saved += 1
        db.commit()
        return saved
    finally:
        db.close()


def get_articles(ticker: str, limit: int = 10) -> list[NewsArticle]:
    """Returns cached news articles for a ticker."""
    db: Session = SessionLocal()
    try:
        return (
            db.query(NewsArticle)
            .filter(NewsArticle.ticker == ticker.upper())
            .order_by(NewsArticle.fetched_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


if __name__ == "__main__":
    print("Testing MemoStore...\n")

    # Test save memo
    print("TEST 1: Save memo")
    memo = save_memo({
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "summary": "Apple reported strong Q4 results driven by iPhone 16 demand.",
        "bull_case": "Strong iPhone upgrade cycle, services growth, AI integration.",
        "bear_case": "China slowdown, valuation premium, macro headwinds.",
        "recommendation": "BUY",
        "metrics": {"revenue": "94.9B", "eps": "1.64", "yoy_growth": "6%"},
        "confidence_score": 0.87,
        "flagged_claims": [],
        "sources_used": ["SEC 10-Q", "NewsAPI"]
    })
    print(f"   Saved: {memo.ticker} — {memo.id}")

    # Test retrieve
    print("\nTEST 2: Retrieve memo by ticker")
    retrieved = get_memo_by_ticker("AAPL")
    print(f"   Found: {retrieved.ticker} — {retrieved.recommendation}")
    print(f"   Score: {retrieved.confidence_score}")

    # Test get all
    print("\nTEST 3: Get all memos")
    all_memos = get_all_memos()
    print(f"   Total memos: {len(all_memos)}")

    print("\n✅ MemoStore working correctly!")