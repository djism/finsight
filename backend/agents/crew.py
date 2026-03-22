import sys
import os
import ssl
import certifi
from pathlib import Path

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from backend.agents.fetcher_agent import run_fetcher
from backend.agents.analyst_agent import run_analyst
from backend.agents.critic_agent import run_critic, assemble_final_memo
from backend.schemas.memo import InvestmentMemoSchema
from backend.db.memo_store import save_memo


def run_pipeline(ticker: str) -> dict:
    """
    Master pipeline — orchestrates all 3 agents in sequence.

    Flow:
        Fetcher Agent  → collects SEC filings + news
             ↓
        Analyst Agent  → generates memo from raw data
             ↓
        Critic Agent   → fact-checks + assigns confidence
             ↓
        Final Memo     → saved to PostgreSQL + returned

    Args:
        ticker: Stock ticker symbol e.g. "AAPL", "MSFT", "NVDA"

    Returns:
        dict with full memo data + metadata
    """
    ticker = ticker.upper().strip()

    print(f"\n{'='*55}")
    print(f"  FINSIGHT PIPELINE — {ticker}")
    print(f"  3-Agent Multi-Step Financial Analysis")
    print(f"{'='*55}")

    try:
        # ── Agent 1: Fetcher ──────────────────────────────────────────────────
        print(f"\n[1/3] Running Fetcher Agent...")
        fetcher_output = run_fetcher(ticker)

        # ── Agent 2: Analyst ──────────────────────────────────────────────────
        print(f"\n[2/3] Running Analyst Agent...")
        analyst_output = run_analyst(fetcher_output)

        # ── Agent 3: Critic ───────────────────────────────────────────────────
        print(f"\n[3/3] Running Critic Agent...")
        critic_output = run_critic(analyst_output, fetcher_output)

        # ── Assemble final memo ───────────────────────────────────────────────
        print(f"\n📋 Assembling final memo...")
        final_memo = assemble_final_memo(
            analyst_output, critic_output, fetcher_output
        )

        # ── Save to PostgreSQL ────────────────────────────────────────────────
        print(f"\n💾 Saving to database...")
        db_memo = save_memo(final_memo.to_db_dict())

        # ── Build response ────────────────────────────────────────────────────
        result = {
            "success": True,
            "memo_id": str(db_memo.id),
            "ticker": final_memo.ticker,
            "company_name": final_memo.company_name,
            "recommendation": final_memo.recommendation.value,
            "confidence_score": final_memo.confidence_score,
            "summary": final_memo.summary,
            "bull_case": final_memo.bull_case,
            "bear_case": final_memo.bear_case,
            "metrics": final_memo.metrics.model_dump(),
            "flagged_claims": [f.model_dump() for f in final_memo.flagged_claims],
            "sources": final_memo.sources.model_dump(),
            "created_at": db_memo.created_at.isoformat()
        }

        print(f"\n{'='*55}")
        print(f"  ✅ PIPELINE COMPLETE — {ticker}")
        print(f"{'='*55}")
        print(f"  Recommendation   : {result['recommendation']}")
        print(f"  Confidence Score : {result['confidence_score']:.2f}")
        print(f"  Flagged Claims   : {len(result['flagged_claims'])}")
        print(f"  Memo ID          : {result['memo_id']}")
        print(f"{'='*55}\n")

        return result

    except Exception as e:
        print(f"\n❌ Pipeline failed for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "ticker": ticker,
            "error": str(e)
        }


if __name__ == "__main__":
    import json

    print("Testing FinSight Pipeline...\n")

    # Test with Apple
    result = run_pipeline("AAPL")

    if result["success"]:
        print("\nFINAL RESULT:")
        print(f"Ticker           : {result['ticker']}")
        print(f"Company          : {result['company_name']}")
        print(f"Recommendation   : {result['recommendation']}")
        print(f"Confidence Score : {result['confidence_score']:.2f}")
        print(f"Memo ID          : {result['memo_id']}")
        print(f"\nSummary:")
        print(result['summary'][:400])
        print(f"\nMetrics:")
        for k, v in result['metrics'].items():
            if v:
                print(f"  {k}: {v}")
    else:
        print(f"Pipeline failed: {result.get('error')}")

    print("\n✅ Crew pipeline test complete!")