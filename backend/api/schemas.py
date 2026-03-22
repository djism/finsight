from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze endpoint."""
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol",
        examples=["AAPL", "MSFT", "NVDA", "GOOGL"]
    )


class MetricsResponse(BaseModel):
    """Financial metrics in API response."""
    revenue: Optional[str] = None
    revenue_growth_yoy: Optional[str] = None
    eps: Optional[str] = None
    eps_growth_yoy: Optional[str] = None
    gross_margin: Optional[str] = None
    operating_margin: Optional[str] = None
    debt_to_equity: Optional[str] = None
    free_cash_flow: Optional[str] = None
    guidance: Optional[str] = None
    pe_ratio: Optional[str] = None


class FlaggedClaimResponse(BaseModel):
    """A flagged claim from the Critic agent."""
    claim: str
    reason: str
    severity: str


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze endpoint."""
    success: bool
    memo_id: Optional[str] = None
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    recommendation: Optional[str] = None
    confidence_score: Optional[float] = None
    summary: Optional[str] = None
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None
    metrics: Optional[MetricsResponse] = None
    flagged_claims: Optional[list[FlaggedClaimResponse]] = None
    sources: Optional[dict] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


class MemoListItem(BaseModel):
    """Single item in the memos list response."""
    memo_id: str
    ticker: str
    company_name: Optional[str] = None
    recommendation: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    message: str


if __name__ == "__main__":
    print("Testing API schemas...\n")

    req = AnalyzeRequest(ticker="AAPL")
    print(f"Request  : {req.ticker}")

    resp = AnalyzeResponse(
        success=True,
        memo_id="abc-123",
        ticker="AAPL",
        company_name="Apple Inc.",
        recommendation="HOLD",
        confidence_score=0.80,
        summary="Apple reported strong results...",
        bull_case="Strong revenue | High net income",
        bear_case="No catalyst | Competition",
        metrics=MetricsResponse(revenue="$416B", eps="$7.49"),
        flagged_claims=[],
        created_at="2026-03-22T00:00:00"
    )
    print(f"Response : {resp.ticker} — {resp.recommendation}")
    print(f"Score    : {resp.confidence_score}")

    print("\n✅ API schemas working correctly!")