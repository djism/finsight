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
    AnalystOutput, CriticOutput, FetcherOutput,
    InvestmentMemoSchema, RiskFlag, RiskLevel
)
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


CRITIC_SYSTEM_PROMPT = """You are a critical research reviewer at an investment bank.
Your job is to fact-check investment memos before they reach portfolio managers.

CRITICAL RULES:
- Return ONLY a single valid JSON object — no markdown, no explanation
- No newlines inside string values — use | to separate points
- Be specific about which claims are unsupported or contradicted
- Confidence score: 1.0 = fully supported by data, 0.0 = mostly speculation
- A good memo with solid data support scores 0.7-0.9
- Only flag claims that are genuinely unsupported — don't over-flag"""


CRITIC_PROMPT = """Review this investment memo for {ticker} against the source data.

=== MEMO TO REVIEW ===
Recommendation: {recommendation}
Summary: {summary}
Bull Case: {bull_case}
Bear Case: {bear_case}
Metrics: Revenue={revenue}, EPS={eps}, Gross Margin={gross_margin}

=== SOURCE DATA USED ===
{source_data}

Your job:
1. Check if key claims are supported by the source data
2. Flag any claims that are contradicted or have no data support
3. Assign a confidence score (0.0-1.0)

Return ONLY this JSON:
{{"confidence_score":0.85,"flagged_claims":[{{"claim":"example unsupported claim","reason":"not found in source data","severity":"MEDIUM"}}],"critique_notes":"Overall assessment in one sentence"}}

If no claims are flagged, return empty array: "flagged_claims":[]
IMPORTANT: confidence_score must be a number between 0.0 and 1.0"""


def run_critic(
    analyst_output: AnalystOutput,
    fetcher_output: FetcherOutput
) -> CriticOutput:
    """
    Critic Agent — fact-checks the analyst's memo against source data.

    Responsibilities:
    1. Read the analyst's memo
    2. Cross-check claims against raw source data
    3. Flag contradictions or unsupported claims
    4. Assign a confidence score
    5. Return CriticOutput to complete the pipeline

    This agent is the hallucination detection layer —
    it ensures the memo is grounded in actual data.
    """
    print(f"\n{'='*55}")
    print(f"  CRITIC AGENT — {analyst_output.ticker}")
    print(f"{'='*55}")

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        temperature=0.0,    # zero temp — critic should be deterministic
        max_tokens=1000
    )

    # Build source data context for critic to check against
    source_data = f"{fetcher_output.filings_text[:2000]}\n{fetcher_output.news_text[:1000]}"

    prompt = CRITIC_PROMPT.format(
        ticker=analyst_output.ticker,
        recommendation=analyst_output.recommendation.value,
        summary=analyst_output.summary[:500],
        bull_case=analyst_output.bull_case[:300],
        bear_case=analyst_output.bear_case[:300],
        revenue=analyst_output.metrics.revenue or "N/A",
        eps=analyst_output.metrics.eps or "N/A",
        gross_margin=analyst_output.metrics.gross_margin or "N/A",
        source_data=source_data[:3000]
    )

    print(f"\n🔍 Critic reviewing memo...")
    print(f"   Context size: {len(prompt)} chars")

    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()
    print(f"   ✅ Critic response received ({len(raw)} chars)")

    # Clean and parse JSON
    print(f"\n⚖️  Parsing critic output...")
    cleaned = _clean_json(raw)

    try:
        data = json.loads(cleaned)

        # Parse flagged claims
        flagged = []
        for flag_data in data.get("flagged_claims", []):
            try:
                severity_str = flag_data.get("severity", "MEDIUM").upper()
                try:
                    severity = RiskLevel(severity_str)
                except ValueError:
                    severity = RiskLevel.MEDIUM

                flagged.append(RiskFlag(
                    claim=flag_data.get("claim", ""),
                    reason=flag_data.get("reason", ""),
                    severity=severity
                ))
            except Exception:
                continue

        # Get confidence score
        raw_score = data.get("confidence_score", 0.75)
        if isinstance(raw_score, list):
            confidence = float(raw_score[0])
        else:
            confidence = float(raw_score)
        confidence = max(0.0, min(1.0, confidence))

        output = CriticOutput(
            confidence_score=confidence,
            flagged_claims=flagged,
            critique_notes=data.get("critique_notes", "")
        )

        print(f"   ✅ Critic output parsed")
        print(f"   Confidence score : {output.confidence_score:.2f}")
        print(f"   Flagged claims   : {len(output.flagged_claims)}")
        if output.critique_notes:
            print(f"   Notes            : {output.critique_notes}")

        return output

    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON parse failed: {e}")
        print(f"   Defaulting to conservative confidence score")
        return CriticOutput(
            confidence_score=0.6,
            flagged_claims=[],
            critique_notes="Critic evaluation could not be parsed — using default confidence."
        )


def assemble_final_memo(
    analyst_output: AnalystOutput,
    critic_output: CriticOutput,
    fetcher_output: FetcherOutput
) -> InvestmentMemoSchema:
    """
    Assembles the final investment memo by combining
    Analyst output + Critic review into one validated schema.
    This is the final output of the 3-agent pipeline.
    """
    return InvestmentMemoSchema(
        ticker=analyst_output.ticker,
        company_name=analyst_output.company_name,
        summary=analyst_output.summary,
        bull_case=analyst_output.bull_case,
        bear_case=analyst_output.bear_case,
        recommendation=analyst_output.recommendation,
        metrics=analyst_output.metrics,
        confidence_score=critic_output.confidence_score,
        flagged_claims=critic_output.flagged_claims,
        sources=fetcher_output.sources
    )


def _clean_json(raw: str) -> str:
    """Cleans LLM response to extract valid JSON."""
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            if "{" in part:
                raw = part
                if raw.startswith("json"):
                    raw = raw[4:]
                break

    raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    raw = re.sub(r'\n', ' ', raw)
    raw = re.sub(r'\r', ' ', raw)
    raw = re.sub(r' +', ' ', raw)

    open_braces = raw.count("{")
    close_braces = raw.count("}")
    if open_braces > close_braces:
        raw = raw + "}" * (open_braces - close_braces)

    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)

    return raw.strip()


if __name__ == "__main__":
    from backend.agents.fetcher_agent import run_fetcher
    from backend.agents.analyst_agent import run_analyst

    print("Testing Critic Agent...\n")

    print("Step 1: Fetcher Agent...")
    fetcher_output = run_fetcher("AAPL")

    print("\nStep 2: Analyst Agent...")
    analyst_output = run_analyst(fetcher_output)

    print("\nStep 3: Critic Agent...")
    critic_output = run_critic(analyst_output, fetcher_output)

    print("\nStep 4: Assembling final memo...")
    final_memo = assemble_final_memo(analyst_output, critic_output, fetcher_output)

    print(f"\n{'='*55}")
    print("FINAL INVESTMENT MEMO")
    print(f"{'='*55}")
    print(f"Ticker           : {final_memo.ticker}")
    print(f"Company          : {final_memo.company_name}")
    print(f"Recommendation   : {final_memo.recommendation.value}")
    print(f"Confidence Score : {final_memo.confidence_score:.2f}")
    print(f"Flagged Claims   : {len(final_memo.flagged_claims)}")
    print(f"\nMetrics:")
    print(f"  Revenue        : {final_memo.metrics.revenue}")
    print(f"  EPS            : {final_memo.metrics.eps}")
    print(f"\nSummary:")
    print(final_memo.summary[:400])
    print(f"\nBull Case:")
    print(final_memo.bull_case)
    print(f"\nBear Case:")
    print(final_memo.bear_case)
    if final_memo.flagged_claims:
        print(f"\nFlagged Claims:")
        for flag in final_memo.flagged_claims:
            print(f"  ⚠️  {flag.claim}: {flag.reason} [{flag.severity}]")

    print("\n✅ Full 3-agent pipeline working correctly!")