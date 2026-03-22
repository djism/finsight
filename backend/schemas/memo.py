from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class Recommendation(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class FinancialMetrics(BaseModel):
    """
    Key financial metrics extracted by the Analyst agent
    from SEC filings and earnings transcripts.
    """
    revenue: Optional[str] = Field(None, description="Most recent revenue figure")
    revenue_growth_yoy: Optional[str] = Field(None, description="Year-over-year revenue growth")
    eps: Optional[str] = Field(None, description="Earnings per share")
    eps_growth_yoy: Optional[str] = Field(None, description="YoY EPS growth")
    gross_margin: Optional[str] = Field(None, description="Gross margin %")
    operating_margin: Optional[str] = Field(None, description="Operating margin %")
    debt_to_equity: Optional[str] = Field(None, description="Debt-to-equity ratio")
    free_cash_flow: Optional[str] = Field(None, description="Free cash flow")
    guidance: Optional[str] = Field(None, description="Forward guidance from management")
    pe_ratio: Optional[str] = Field(None, description="Price-to-earnings ratio")


class RiskFlag(BaseModel):
    """
    A contradiction or unsupported claim flagged by the Critic agent.
    """
    claim: str = Field(description="The specific claim being flagged")
    reason: str = Field(description="Why this claim is flagged or contradicted")
    severity: RiskLevel = Field(default=RiskLevel.MEDIUM)


class DataSources(BaseModel):
    """
    Tracks which data sources were used to generate the memo.
    """
    sec_filings: list[str] = Field(default_factory=list)
    news_articles: list[str] = Field(default_factory=list)
    filing_dates: list[str] = Field(default_factory=list)


# ── Core memo schema ──────────────────────────────────────────────────────────

class InvestmentMemoSchema(BaseModel):
    """
    The fully structured investment memo produced by the 3-agent pipeline.
    Every field is validated by Pydantic before being saved to PostgreSQL.

    Flow:
        Fetcher agent → raw data
        Analyst agent → fills most fields
        Critic agent  → fills confidence_score + flagged_claims
    """
    # Identity
    ticker: str = Field(description="Stock ticker symbol e.g. AAPL")
    company_name: str = Field(description="Full company name")

    # Analyst output
    summary: str = Field(
        description="2-3 paragraph investment narrative covering business, "
                    "recent performance, and forward outlook"
    )
    bull_case: str = Field(
        description="3-5 specific positive factors supporting investment"
    )
    bear_case: str = Field(
        description="3-5 specific risk factors and headwinds"
    )
    recommendation: Recommendation = Field(
        description="Overall recommendation: BUY, HOLD, or SELL"
    )
    metrics: FinancialMetrics = Field(
        description="Structured financial metrics extracted from filings"
    )

    # Critic output
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Critic's confidence in memo accuracy (0.0-1.0)"
    )
    flagged_claims: list[RiskFlag] = Field(
        default_factory=list,
        description="Claims the Critic flagged as contradicted or unsupported"
    )

    # Sources
    sources: DataSources = Field(
        default_factory=DataSources,
        description="Data sources used to generate this memo"
    )

    def to_db_dict(self) -> dict:
        """Converts to flat dict for database storage."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "summary": self.summary,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "recommendation": self.recommendation.value,
            "metrics": self.metrics.model_dump(),
            "confidence_score": self.confidence_score,
            "flagged_claims": [f.model_dump() for f in self.flagged_claims],
            "sources_used": self.sources.model_dump()
        }

    def to_markdown(self) -> str:
        """Formats memo as clean markdown for display."""
        flags_text = ""
        if self.flagged_claims:
            flags_text = "\n## ⚠️ Flagged Claims\n"
            for flag in self.flagged_claims:
                flags_text += f"- **{flag.claim}**: {flag.reason} [{flag.severity}]\n"

        metrics = self.metrics
        metrics_text = "\n".join([
            f"| Revenue | {metrics.revenue or 'N/A'} |",
            f"| Revenue Growth YoY | {metrics.revenue_growth_yoy or 'N/A'} |",
            f"| EPS | {metrics.eps or 'N/A'} |",
            f"| Gross Margin | {metrics.gross_margin or 'N/A'} |",
            f"| Free Cash Flow | {metrics.free_cash_flow or 'N/A'} |",
            f"| Guidance | {metrics.guidance or 'N/A'} |",
        ])

        return f"""# {self.company_name} ({self.ticker}) — Investment Memo

## Recommendation: {self.recommendation.value} | Confidence: {self.confidence_score:.0%}

## Summary
{self.summary}

## Bull Case
{self.bull_case}

## Bear Case
{self.bear_case}

## Key Metrics
| Metric | Value |
|--------|-------|
{metrics_text}
{flags_text}
## Sources
- SEC Filings: {', '.join(self.sources.sec_filings) or 'None'}
- News: {', '.join(self.sources.news_articles[:3]) or 'None'}
"""


# ── Partial schemas for agent intermediate outputs ────────────────────────────

class FetcherOutput(BaseModel):
    """What the Fetcher agent returns after data collection."""
    ticker: str
    company_name: Optional[str] = None
    filings_text: str = Field(description="Combined text from SEC filings")
    news_text: str = Field(description="Combined text from news articles")
    sources: DataSources = Field(default_factory=DataSources)


class AnalystOutput(BaseModel):
    """What the Analyst agent returns before critic review."""
    ticker: str
    company_name: str
    summary: str
    bull_case: str
    bear_case: str
    recommendation: Recommendation
    metrics: FinancialMetrics


class CriticOutput(BaseModel):
    """What the Critic agent adds to the analyst's work."""
    confidence_score: float = Field(ge=0.0, le=1.0)
    flagged_claims: list[RiskFlag] = Field(default_factory=list)
    critique_notes: Optional[str] = None


if __name__ == "__main__":
    print("Testing schemas...\n")

    # Test full memo
    memo = InvestmentMemoSchema(
        ticker="AAPL",
        company_name="Apple Inc.",
        summary="Apple reported strong Q4 FY2024 results with iPhone 16 driving demand.",
        bull_case="1. iPhone upgrade cycle accelerating\n2. Services revenue at all-time high\n3. AI integration across product line",
        bear_case="1. China market slowdown\n2. Premium valuation\n3. Macro uncertainty",
        recommendation=Recommendation.BUY,
        metrics=FinancialMetrics(
            revenue="94.9B",
            revenue_growth_yoy="6%",
            eps="1.64",
            gross_margin="46.2%",
            guidance="Q1 FY2025 revenue $124B-$127B"
        ),
        confidence_score=0.87,
        flagged_claims=[
            RiskFlag(
                claim="Services revenue will double in 2 years",
                reason="No supporting data found in SEC filing",
                severity=RiskLevel.MEDIUM
            )
        ],
        sources=DataSources(
            sec_filings=["AAPL 10-Q Q4 2024"],
            news_articles=["Apple beats earnings", "iPhone 16 demand strong"],
            filing_dates=["2024-11-01"]
        )
    )

    print(f"Ticker          : {memo.ticker}")
    print(f"Recommendation  : {memo.recommendation}")
    print(f"Confidence      : {memo.confidence_score}")
    print(f"Flagged claims  : {len(memo.flagged_claims)}")
    print(f"\nMarkdown preview:\n{memo.to_markdown()[:400]}...")
    print(f"\nDB dict keys: {list(memo.to_db_dict().keys())}")
    print("\n✅ Schemas working correctly!")