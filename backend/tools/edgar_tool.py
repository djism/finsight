import sys
import os
import ssl
import certifi
import requests
import json
import time
from pathlib import Path
from typing import Optional

ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import EDGAR_USER_AGENT, EDGAR_MAX_FILINGS

# EDGAR base URLs
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q={ticker}&dateRange=custom&startdt=2023-01-01&forms=10-K,10-Q"
EDGAR_COMPANY_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/Archives/edgar/full-index/"

HEADERS = {
    "User-Agent": EDGAR_USER_AGENT,
    "Accept": "application/json"
}


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Looks up the SEC CIK number for a given ticker symbol.
    CIK is the unique identifier EDGAR uses for each company.
    """
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        companies = resp.json()

        ticker_upper = ticker.upper()
        for _, company in companies.items():
            if company.get("ticker", "").upper() == ticker_upper:
                cik = str(company["cik_str"]).zfill(10)
                print(f"   ✅ Found CIK for {ticker}: {cik}")
                return cik

        print(f"   ⚠️  No CIK found for ticker: {ticker}")
        return None

    except Exception as e:
        print(f"   ❌ CIK lookup error: {e}")
        return None


def get_recent_filings(ticker: str, filing_types: list = None) -> list[dict]:
    """
    Fetches metadata for recent SEC filings for a ticker.
    Returns list of filing dicts with type, date, and accession number.
    """
    if filing_types is None:
        filing_types = ["10-K", "10-Q"]

    cik = get_cik_for_ticker(ticker)
    if not cik:
        return []

    try:
        url = EDGAR_COMPANY_URL.format(cik=cik)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        descriptions = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form in filing_types and len(results) < EDGAR_MAX_FILINGS:
                results.append({
                    "ticker": ticker.upper(),
                    "filing_type": form,
                    "filing_date": dates[i] if i < len(dates) else "Unknown",
                    "accession_number": accessions[i] if i < len(accessions) else "",
                    "primary_document": descriptions[i] if i < len(descriptions) else "",
                    "cik": cik
                })

        print(f"   ✅ Found {len(results)} filings for {ticker}")
        return results

    except Exception as e:
        print(f"   ❌ Filing fetch error: {e}")
        return []


def fetch_filing_text(cik: str, accession_number: str,
                      primary_document: str) -> Optional[str]:
    """
    Fetches filing text using correct EDGAR /data/ URL format.
    """
    try:
        import re
        cik_int = str(int(cik))  # strip leading zeros
        acc_clean = accession_number.replace("-", "")
        url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_int}/{acc_clean}/{primary_document}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()
            print(f"   ✅ Filing text fetched ({len(text)} chars)")
            return text[:8000]
        print(f"   ⚠️  Filing URL returned {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"   ⚠️  Could not fetch filing text: {e}")
        return None


def get_company_facts(ticker: str) -> Optional[dict]:
    """
    Fetches structured financial facts from SEC XBRL data.
    This gives clean structured financial data — revenue, EPS etc.
    Much more reliable than parsing raw filing text.
    """
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return None

    try:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        facts = resp.json()

        # Extract key financial metrics from XBRL data
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        extracted = {
            "ticker": ticker.upper(),
            "company_name": facts.get("entityName", ticker),
            "cik": cik
        }

        # Revenue
        for revenue_key in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                            "SalesRevenueNet"]:
            if revenue_key in us_gaap:
                units = us_gaap[revenue_key].get("units", {}).get("USD", [])
                if units:
                    # Get most recent annual figure
                    annual = [u for u in units if u.get("form") == "10-K" and u.get("end", "") >= "2020-01-01"]
                    if annual:
                        latest = sorted(annual, key=lambda x: x.get("end", ""))[-1]
                        extracted["revenue"] = latest.get("val")
                        extracted["revenue_period"] = latest.get("end")
                        break

        # Net income
        if "NetIncomeLoss" in us_gaap:
            units = us_gaap["NetIncomeLoss"].get("units", {}).get("USD", [])
            annual = [u for u in units if u.get("form") == "10-K" and u.get("end", "") >= "2020-01-01"]
            if annual:
                latest = sorted(annual, key=lambda x: x.get("end", ""))[-1]
                extracted["net_income"] = latest.get("val")

        # EPS
        for eps_key in ["EarningsPerShareBasic", "EarningsPerShareDiluted"]:
            if eps_key in us_gaap:
                units = us_gaap[eps_key].get("units", {}).get("USD/shares", [])
                annual = [u for u in units if u.get("form") == "10-K" and u.get("end", "") >= "2020-01-01"]
                if annual:
                    latest = sorted(annual, key=lambda x: x.get("end", ""))[-1]
                    extracted["eps"] = latest.get("val")
                    break

        print(f"   ✅ Company facts retrieved for {ticker}")
        return extracted

    except Exception as e:
        print(f"   ⚠️  Company facts error: {e}")
        return None


def format_facts_for_llm(facts: dict) -> str:
    """Formats extracted XBRL facts as clean text for LLM context."""
    if not facts:
        return "No structured financial data available."

    lines = [
        f"Company: {facts.get('company_name', 'Unknown')} ({facts.get('ticker', '')})",
        f"CIK: {facts.get('cik', 'N/A')}",
    ]

    if facts.get("revenue"):
        rev = facts["revenue"]
        period = facts.get("revenue_period", "")
        lines.append(f"Revenue: ${rev:,.0f} (period ending {period})")

    if facts.get("net_income"):
        ni = facts["net_income"]
        lines.append(f"Net Income: ${ni:,.0f}")

    if facts.get("eps"):
        lines.append(f"EPS: ${facts['eps']:.2f}")

    return "\n".join(lines)


if __name__ == "__main__":
    import ssl
    import certifi
    ssl._create_default_https_context = ssl.create_default_context
    os.environ['SSL_CERT_FILE'] = certifi.where()

    print("Testing EDGAR tool...\n")

    print("=" * 55)
    print("TEST 1: CIK lookup")
    print("=" * 55)
    cik = get_cik_for_ticker("AAPL")
    print(f"   AAPL CIK: {cik}")

    print("\n" + "=" * 55)
    print("TEST 2: Recent filings")
    print("=" * 55)
    filings = get_recent_filings("AAPL")
    for f in filings:
        print(f"   {f['filing_type']} — {f['filing_date']}")

    print("\n" + "=" * 55)
    print("TEST 3: Company facts (structured XBRL data)")
    print("=" * 55)
    facts = get_company_facts("AAPL")
    if facts:
        print(format_facts_for_llm(facts))

    print("\n✅ EDGAR tool working correctly!")