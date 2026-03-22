import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

sys.path.append(str(Path(__file__).resolve().parents[2]))
from backend.api.schemas import (
    AnalyzeRequest, AnalyzeResponse, MemoListItem,
    HealthResponse, MetricsResponse, FlaggedClaimResponse
)
from backend.agents.crew import run_pipeline
from backend.db.memo_store import get_memo_by_ticker, get_all_memos
from backend.db.database import check_connection
from backend.output.pdf_generator import generate_memo_pdf

router = APIRouter()


# ── Health check ──────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — verifies API and database are running."""
    db_ok = check_connection()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database="connected" if db_ok else "disconnected",
        message="FinSight API is ready!" if db_ok else "Database not connected."
    )


# ── Analyze endpoint ──────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_ticker(request: AnalyzeRequest):
    """
    Main endpoint — runs the 3-agent pipeline for a ticker.

    Runs:
    1. Fetcher Agent  — SEC EDGAR + news
    2. Analyst Agent  — investment memo generation
    3. Critic Agent   — fact-checking + confidence scoring

    Returns structured investment memo saved to PostgreSQL.
    """
    ticker = request.ticker.upper().strip()

    try:
        result = run_pipeline(ticker)

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Pipeline failed")
            )

        # Build metrics response
        metrics_data = result.get("metrics", {})
        metrics = MetricsResponse(
            revenue=metrics_data.get("revenue"),
            revenue_growth_yoy=metrics_data.get("revenue_growth_yoy"),
            eps=metrics_data.get("eps"),
            eps_growth_yoy=metrics_data.get("eps_growth_yoy"),
            gross_margin=metrics_data.get("gross_margin"),
            operating_margin=metrics_data.get("operating_margin"),
            debt_to_equity=metrics_data.get("debt_to_equity"),
            free_cash_flow=metrics_data.get("free_cash_flow"),
            guidance=metrics_data.get("guidance"),
            pe_ratio=metrics_data.get("pe_ratio")
        )

        # Build flagged claims response
        flagged = [
            FlaggedClaimResponse(
                claim=f.get("claim", ""),
                reason=f.get("reason", ""),
                severity=f.get("severity", "MEDIUM")
            )
            for f in result.get("flagged_claims", [])
        ]

        return AnalyzeResponse(
            success=True,
            memo_id=result.get("memo_id"),
            ticker=result.get("ticker"),
            company_name=result.get("company_name"),
            recommendation=result.get("recommendation"),
            confidence_score=result.get("confidence_score"),
            summary=result.get("summary"),
            bull_case=result.get("bull_case"),
            bear_case=result.get("bear_case"),
            metrics=metrics,
            flagged_claims=flagged,
            sources=result.get("sources"),
            created_at=result.get("created_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Get memo by ticker ────────────────────────────────────────────────────────

@router.get("/memo/{ticker}", response_model=AnalyzeResponse)
async def get_memo(ticker: str):
    """
    Returns the most recent memo for a given ticker.
    Does NOT re-run the pipeline — returns cached result.
    """
    memo = get_memo_by_ticker(ticker.upper())

    if not memo:
        raise HTTPException(
            status_code=404,
            detail=f"No memo found for {ticker.upper()}. "
                   f"Run POST /analyze first."
        )

    metrics_data = memo.metrics or {}
    metrics = MetricsResponse(
        revenue=metrics_data.get("revenue"),
        revenue_growth_yoy=metrics_data.get("revenue_growth_yoy"),
        eps=metrics_data.get("eps"),
        eps_growth_yoy=metrics_data.get("eps_growth_yoy"),
        gross_margin=metrics_data.get("gross_margin"),
        operating_margin=metrics_data.get("operating_margin"),
        debt_to_equity=metrics_data.get("debt_to_equity"),
        free_cash_flow=metrics_data.get("free_cash_flow"),
        guidance=metrics_data.get("guidance"),
        pe_ratio=metrics_data.get("pe_ratio")
    )

    flagged = [
        FlaggedClaimResponse(
            claim=f.get("claim", ""),
            reason=f.get("reason", ""),
            severity=f.get("severity", "MEDIUM")
        )
        for f in (memo.flagged_claims or [])
    ]

    return AnalyzeResponse(
        success=True,
        memo_id=str(memo.id),
        ticker=memo.ticker,
        company_name=memo.company_name,
        recommendation=memo.recommendation,
        confidence_score=memo.confidence_score,
        summary=memo.summary,
        bull_case=memo.bull_case,
        bear_case=memo.bear_case,
        metrics=metrics,
        flagged_claims=flagged,
        sources=memo.sources_used,
        created_at=memo.created_at.isoformat() if memo.created_at else None
    )


# ── List all memos ────────────────────────────────────────────────────────────

@router.get("/memos", response_model=list[MemoListItem])
async def list_memos(limit: int = 20):
    """Returns a list of all analyzed tickers with basic info."""
    memos = get_all_memos(limit=limit)
    return [
        MemoListItem(
            memo_id=str(m.id),
            ticker=m.ticker,
            company_name=m.company_name,
            recommendation=m.recommendation,
            confidence_score=m.confidence_score,
            created_at=m.created_at.isoformat() if m.created_at else ""
        )
        for m in memos
    ]


# ── Download PDF ──────────────────────────────────────────────────────────────

@router.get("/memo/{ticker}/pdf")
async def download_pdf(ticker: str):
    """
    Generates and returns a PDF memo for the most recent
    analysis of the given ticker.
    """
    memo = get_memo_by_ticker(ticker.upper())

    if not memo:
        raise HTTPException(
            status_code=404,
            detail=f"No memo found for {ticker.upper()}. Run POST /analyze first."
        )

    memo_dict = memo.to_dict()
    pdf_path = generate_memo_pdf(memo_dict)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticker.upper()}_investment_memo.pdf"
    )


# ── Example tickers ───────────────────────────────────────────────────────────

@router.get("/examples")
async def get_examples():
    """Returns example tickers to try."""
    return {
        "examples": {
            "tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
            "finance": ["JPM", "GS", "BAC", "MS"],
            "healthcare": ["JNJ", "PFE", "UNH"],
            "energy": ["XOM", "CVX"],
            "consumer": ["AMZN", "WMT", "TSLA"]
        },
        "note": "POST /analyze with any NYSE/NASDAQ ticker"
    }