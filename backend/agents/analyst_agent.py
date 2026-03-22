import sys
import os
import ssl
import certifi
import json
import re
from pathlib import Path

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import GROQ_API_KEY, LLM_MODEL
from backend.schemas.memo import (
    FetcherOutput, AnalystOutput, FinancialMetrics, Recommendation
)
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


ANALYST_SYSTEM_PROMPT = """You are a senior financial analyst at a top investment bank.
Your job is to analyze SEC filings and news to produce rigorous, data-driven investment research.

CRITICAL RULES:
- Return ONLY a single valid JSON object — no markdown, no code blocks, no explanation
- All string values must be on ONE line — no newlines inside string values
- Use | to separate multiple points within a single string value
- Only use facts explicitly present in the provided data
- Always cite specific numbers when available
- If data is missing for a field, use null"""


ANALYST_PROMPT = """Analyze the following financial data for {ticker} ({company_name}).

=== FINANCIAL DATA ===
{filings_text}

=== RECENT NEWS ===
{news_text}

Return ONLY this JSON object with no newlines inside string values:
{{"ticker":"{ticker}","company_name":"{company_name}","summary":"Single paragraph investment narrative with specific numbers covering business performance and outlook — no line breaks","bull_case":"Factor 1 with data | Factor 2 with data | Factor 3 with data","bear_case":"Risk 1 with data | Risk 2 with data | Risk 3 with data","recommendation":"BUY or HOLD or SELL or INSUFFICIENT_DATA","metrics":{{"revenue":"most recent revenue with period","revenue_growth_yoy":"YoY growth % or null","eps":"EPS value or null","eps_growth_yoy":"EPS growth % or null","gross_margin":"gross margin % or null","operating_margin":"operating margin % or null","debt_to_equity":"D/E ratio or null","free_cash_flow":"FCF or null","guidance":"forward guidance or null","pe_ratio":"P/E or null"}}}}

IMPORTANT: Return only the JSON above. No text before or after. No newlines inside string values."""


def clean_json_response(raw: str) -> str:
    """
    Cleans LLM response to extract valid JSON.
    Handles common issues: markdown blocks, newlines in strings,
    trailing commas, truncated responses.
    """
    # Strip markdown code blocks
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            if "{" in part:
                raw = part
                if raw.startswith("json"):
                    raw = raw[4:]
                break

    raw = raw.strip()

    # Find the JSON object boundaries
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    # Replace all newlines and excessive whitespace
    raw = re.sub(r'\n', ' ', raw)
    raw = re.sub(r'\r', ' ', raw)
    raw = re.sub(r'\t', ' ', raw)
    raw = re.sub(r' +', ' ', raw)

    # Fix truncated JSON — add missing closing braces/brackets
    open_braces = raw.count("{")
    close_braces = raw.count("}")
    open_brackets = raw.count("[")
    close_brackets = raw.count("]")

    if open_brackets > close_brackets:
        raw = raw + "]" * (open_brackets - close_brackets)
    if open_braces > close_braces:
        raw = raw + "}" * (open_braces - close_braces)

    # Remove trailing commas before closing braces/brackets
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)

    return raw.strip()


def run_analyst(fetcher_output: FetcherOutput) -> AnalystOutput:
    """
    Analyst Agent — generates investment memo from raw data.

    Responsibilities:
    1. Read all data collected by the Fetcher agent
    2. Extract key financial metrics
    3. Build investment narrative (summary, bull case, bear case)
    4. Make a recommendation
    5. Return structured AnalystOutput for the Critic agent
    """
    print(f"\n{'='*55}")
    print(f"  ANALYST AGENT — {fetcher_output.ticker}")
    print(f"{'='*55}")

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        temperature=0.1,
        max_tokens=3000
    )

    prompt = ANALYST_PROMPT.format(
        ticker=fetcher_output.ticker,
        company_name=fetcher_output.company_name,
        filings_text=fetcher_output.filings_text[:4000],
        news_text=fetcher_output.news_text[:2000]
    )

    print(f"\n🤔 Analyst reading filings and news...")
    print(f"   Context size: {len(prompt)} chars")

    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()
    print(f"   ✅ Response received ({len(raw)} chars)")

    # Clean and parse JSON
    print(f"\n📊 Parsing analyst output...")
    cleaned = clean_json_response(raw)

    try:
        data = json.loads(cleaned)

        metrics_data = data.get("metrics", {})
        metrics = FinancialMetrics(
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

        rec_str = data.get("recommendation", "INSUFFICIENT_DATA").upper()
        try:
            recommendation = Recommendation(rec_str)
        except ValueError:
            recommendation = Recommendation.INSUFFICIENT_DATA

        output = AnalystOutput(
            ticker=fetcher_output.ticker,
            company_name=fetcher_output.company_name,
            summary=data.get("summary", ""),
            bull_case=data.get("bull_case", ""),
            bear_case=data.get("bear_case", ""),
            recommendation=recommendation,
            metrics=metrics
        )

        print(f"   ✅ Parsed successfully")
        print(f"   Recommendation : {output.recommendation}")
        print(f"   Revenue        : {output.metrics.revenue}")
        print(f"   EPS            : {output.metrics.eps}")

        return output

    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON parse failed: {e}")
        print(f"   Cleaned JSON: {cleaned[:300]}")

        # Graceful fallback — extract what we can
        return AnalystOutput(
            ticker=fetcher_output.ticker,
            company_name=fetcher_output.company_name,
            summary=f"Analysis for {fetcher_output.ticker}: {raw[:400]}",
            bull_case="Could not parse structured response.",
            bear_case="Could not parse structured response.",
            recommendation=Recommendation.INSUFFICIENT_DATA,
            metrics=FinancialMetrics()
        )


if __name__ == "__main__":
    from backend.agents.fetcher_agent import run_fetcher

    print("Testing Analyst Agent...\n")

    print("Step 1: Running Fetcher Agent...")
    fetcher_output = run_fetcher("AAPL")

    print("\nStep 2: Running Analyst Agent...")
    analyst_output = run_analyst(fetcher_output)

    print(f"\n{'='*55}")
    print("ANALYST OUTPUT")
    print(f"{'='*55}")
    print(f"Ticker         : {analyst_output.ticker}")
    print(f"Company        : {analyst_output.company_name}")
    print(f"Recommendation : {analyst_output.recommendation}")
    print(f"\nMetrics:")
    print(f"  Revenue      : {analyst_output.metrics.revenue}")
    print(f"  EPS          : {analyst_output.metrics.eps}")
    print(f"  Gross Margin : {analyst_output.metrics.gross_margin}")
    print(f"  Guidance     : {analyst_output.metrics.guidance}")
    print(f"\nSummary:")
    print(analyst_output.summary[:500])
    print(f"\nBull case:")
    print(analyst_output.bull_case[:300])
    print(f"\nBear case:")
    print(analyst_output.bear_case[:300])

    print("\n✅ Analyst Agent working correctly!")