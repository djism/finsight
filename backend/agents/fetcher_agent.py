import sys
import os
import ssl
import certifi
from pathlib import Path

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import GROQ_API_KEY, LLM_MODEL
from backend.tools.edgar_tool import (
    get_recent_filings,
    get_company_facts,
    format_facts_for_llm,
    fetch_filing_text,
    get_cik_for_ticker
)
from backend.tools.news_tool import fetch_company_news, format_articles_for_llm
from backend.db.memo_store import save_filing, save_articles
from backend.schemas.memo import FetcherOutput, DataSources


def run_fetcher(ticker: str) -> FetcherOutput:
    """
    Fetcher Agent — collects all raw data for a ticker.

    Responsibilities:
    1. Fetch SEC filings metadata + XBRL financial facts
    2. Fetch recent news articles
    3. Cache everything in PostgreSQL
    4. Return structured FetcherOutput for the Analyst agent

    This agent never generates opinions — it only gathers facts.
    """
    print(f"\n{'='*55}")
    print(f"  FETCHER AGENT — {ticker.upper()}")
    print(f"{'='*55}")

    ticker = ticker.upper()
    sources = DataSources()

    # ── Step 1: Get company name from EDGAR ───────────────────────────────────
    print(f"\n📋 Step 1: Looking up company info...")
    facts = get_company_facts(ticker)
    company_name = facts.get("company_name", ticker) if facts else ticker
    print(f"   Company: {company_name}")

    # ── Step 2: Fetch SEC filings ─────────────────────────────────────────────
    print(f"\n📄 Step 2: Fetching SEC filings...")
    filings_text_parts = []

    # Get structured XBRL facts (most reliable financial data)
    if facts:
        facts_text = format_facts_for_llm(facts)
        filings_text_parts.append("=== STRUCTURED FINANCIAL DATA (SEC XBRL) ===")
        filings_text_parts.append(facts_text)
        sources.sec_filings.append("SEC XBRL Company Facts")

    # Get recent filing metadata
    filings = get_recent_filings(ticker, ["10-K", "10-Q"])

    for filing in filings:
        filing_label = f"{filing['filing_type']} ({filing['filing_date']})"
        sources.sec_filings.append(filing_label)
        sources.filing_dates.append(filing['filing_date'])

        # Try to fetch actual filing text
        if filing.get("accession_number") and filing.get("primary_document"):
            print(f"   Fetching text: {filing_label}...")
            text = fetch_filing_text(
                filing["cik"],
                filing["accession_number"],
                filing["primary_document"]
            )
            if text:
                filings_text_parts.append(f"\n=== {filing_label} ===")
                filings_text_parts.append(text[:3000])  # first 3000 chars

                # Cache in DB
                save_filing(
                    ticker=ticker,
                    filing_type=filing["filing_type"],
                    content=text[:10000],
                    filing_date=filing["filing_date"],
                    url=filing.get("url")
                )

    filings_text = "\n".join(filings_text_parts) if filings_text_parts else (
        f"No SEC filing data available for {ticker}."
    )

    # ── Step 3: Fetch news ────────────────────────────────────────────────────
    print(f"\n📰 Step 3: Fetching news articles...")
    articles = fetch_company_news(ticker, company_name, days_back=30)
    news_text = format_articles_for_llm(articles, ticker)

    # Cache articles in DB
    if articles:
        saved = save_articles(ticker, articles)
        print(f"   Cached {saved} articles in database")

    for article in articles:
        title = article.get("title", "")
        if title:
            sources.news_articles.append(title[:100])

    # ── Step 4: Package output ────────────────────────────────────────────────
    print(f"\n✅ Fetcher complete for {ticker}")
    print(f"   SEC sources : {len(sources.sec_filings)}")
    print(f"   News articles: {len(articles)}")
    print(f"   Filing text  : {len(filings_text)} chars")
    print(f"   News text    : {len(news_text)} chars")

    return FetcherOutput(
        ticker=ticker,
        company_name=company_name,
        filings_text=filings_text,
        news_text=news_text,
        sources=sources
    )


if __name__ == "__main__":
    print("Testing Fetcher Agent...\n")

    result = run_fetcher("AAPL")

    print(f"\n{'='*55}")
    print("FETCHER OUTPUT SUMMARY")
    print(f"{'='*55}")
    print(f"Ticker       : {result.ticker}")
    print(f"Company      : {result.company_name}")
    print(f"SEC sources  : {result.sources.sec_filings}")
    print(f"News count   : {len(result.sources.news_articles)}")
    print(f"\nFilings text preview:")
    print(result.filings_text[:400])
    print(f"\nNews text preview:")
    print(result.news_text[:400])
    print("\n✅ Fetcher Agent working correctly!")