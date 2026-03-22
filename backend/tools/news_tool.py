import sys
import os
import ssl
import certifi
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import NEWS_API_KEY, NEWS_MAX_ARTICLES

NEWS_API_URL = "https://newsapi.org/v2/everything"


def fetch_company_news(
    ticker: str,
    company_name: Optional[str] = None,
    days_back: int = 30
) -> list[dict]:
    """
    Fetches recent news articles about a company from NewsAPI.

    Args:
        ticker: Stock ticker e.g. "AAPL"
        company_name: Optional full name e.g. "Apple" for better results
        days_back: How many days back to search (default 30)

    Returns:
        List of article dicts with title, description, content, source, url
    """
    if not NEWS_API_KEY:
        print("   ⚠️  NEWS_API_KEY not set — skipping news fetch")
        return []

    # Build search query — use company name if available, ticker otherwise
    query = f'{ticker} stock earnings'

    # Date range
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "q": query,
        "language": "en",
        "pageSize": NEWS_MAX_ARTICLES,
        "apiKey": NEWS_API_KEY
    }

    try:
        print(f"   🔍 Fetching news for {ticker}...")
        resp = requests.get(NEWS_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            print(f"   ⚠️  NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        articles = data.get("articles", [])
        print(f"   ✅ Found {len(articles)} articles for {ticker}")
        return articles

    except Exception as e:
        print(f"   ❌ News fetch error: {e}")
        return []


def format_articles_for_llm(
    articles: list[dict],
    ticker: str
) -> str:
    """
    Formats news articles as clean text for LLM context.
    Keeps it concise — title + description + source per article.
    """
    if not articles:
        return f"No recent news found for {ticker}."

    lines = [f"RECENT NEWS FOR {ticker.upper()}:", "=" * 40]

    for i, article in enumerate(articles, 1):
        title = article.get("title", "No title")
        description = article.get("description", "")
        source = article.get("source", {})
        source_name = source.get("name", "Unknown") if isinstance(
            source, dict) else str(source)
        published = article.get("publishedAt", "")[:10]

        lines.append(f"\n[Article {i}]")
        lines.append(f"Title  : {title}")
        if description:
            lines.append(f"Summary: {description[:200]}")
        lines.append(f"Source : {source_name} ({published})")
        lines.append("-" * 40)

    return "\n".join(lines)


def get_news_summary(
    ticker: str,
    company_name: Optional[str] = None,
    articles: Optional[list[dict]] = None
) -> str:
    """
    Convenience function — fetches news and returns
    formatted text ready for LLM context.
    Pass articles directly to avoid a second API call.
    """
    if articles is None:
        articles = fetch_company_news(ticker, company_name)
    return format_articles_for_llm(articles, ticker)


if __name__ == "__main__":
    print("Testing News tool...\n")

    print("=" * 55)
    print("TEST 1: Fetch news for AAPL")
    print("=" * 55)
    articles = fetch_company_news("AAPL", "Apple", days_back=14)

    if articles:
        for i, a in enumerate(articles[:3], 1):
            print(f"\nArticle {i}:")
            print(f"  Title  : {a.get('title', '')[:80]}")
            print(f"  Source : {a.get('source', {}).get('name', '')}")
            print(f"  Date   : {a.get('publishedAt', '')[:10]}")
    else:
        print("   No articles returned")

    print("\n" + "=" * 55)
    print("TEST 2: Formatted for LLM")
    print("=" * 55)
    formatted = get_news_summary("AAPL", "Apple")
    print(formatted[:600])

    print("\n✅ News tool working correctly!")