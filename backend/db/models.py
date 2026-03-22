import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid

sys.path.append(str(Path(__file__).resolve().parents[2]))
from backend.db.database import Base


class InvestmentMemo(Base):
    """
    Stores generated investment memos.
    Each memo is produced by the 3-agent pipeline for one ticker.
    """
    __tablename__ = "investment_memos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Core memo content
    summary = Column(Text, nullable=True)           # analyst narrative summary
    bull_case = Column(Text, nullable=True)         # positive factors
    bear_case = Column(Text, nullable=True)         # risk factors
    recommendation = Column(String(50), nullable=True)  # BUY / HOLD / SELL

    # Structured metrics extracted by analyst agent
    metrics = Column(JSON, nullable=True)           # revenue, EPS, guidance etc.

    # Critic agent output
    confidence_score = Column(Float, nullable=True) # 0.0 to 1.0
    flagged_claims = Column(JSON, nullable=True)    # contradictions found

    # Sources used
    sources_used = Column(JSON, nullable=True)      # list of source URLs/names

    # PDF path
    pdf_path = Column(String(500), nullable=True)   # path to generated PDF

    # Vector embedding of the summary for similarity search
    embedding = Column(Vector(384), nullable=True)  # BAAI/bge-small-en-v1.5 dim

    def __repr__(self):
        return f"<InvestmentMemo ticker={self.ticker} created={self.created_at}>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "ticker": self.ticker,
            "company_name": self.company_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "summary": self.summary,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "recommendation": self.recommendation,
            "metrics": self.metrics,
            "confidence_score": self.confidence_score,
            "flagged_claims": self.flagged_claims,
            "sources_used": self.sources_used,
            "pdf_path": self.pdf_path
        }


class RawFiling(Base):
    """
    Stores raw SEC filings fetched by the Fetcher agent.
    Cached to avoid re-fetching on every run.
    """
    __tablename__ = "raw_filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(10), nullable=False, index=True)
    filing_type = Column(String(20), nullable=False)    # 10-K, 10-Q, 8-K
    filing_date = Column(String(20), nullable=True)
    content = Column(Text, nullable=True)               # raw text of filing
    url = Column(String(500), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RawFiling ticker={self.ticker} type={self.filing_type}>"


class NewsArticle(Base):
    """
    Stores news articles fetched by the Fetcher agent.
    """
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(10), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    published_at = Column(String(50), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NewsArticle ticker={self.ticker} title={self.title[:50] if self.title else ''}>"


if __name__ == "__main__":
    print("Testing models...\n")

    from backend.db.database import engine, check_connection

    if not check_connection():
        print("❌ Database not connected")
        exit(1)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully")
    print("\nTables:")
    for table in Base.metadata.tables.keys():
        print(f"   - {table}")