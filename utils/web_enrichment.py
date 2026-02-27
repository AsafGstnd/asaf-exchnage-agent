"""
Web enrichment utilities for real-time external data.
Uses public APIs (Wikipedia, etc.) - no API keys required.
"""
import requests
import urllib.parse
import logging
from typing import Optional

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = 5
USER_AGENT = "FezExchangeAgent/1.0 (University Exchange Recommendation; edu project)"


def fetch_wikipedia_summary(article_title: str) -> Optional[str]:
    """
    Fetch a short Wikipedia summary for a given article title.
    Uses the public REST API - no API key required.
    Returns None on failure (network error, page not found, etc.).
    """
    try:
        encoded = urllib.parse.quote(article_title.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        extract = data.get("extract")
        return (extract[:400] + "...") if extract and len(extract) > 400 else (extract or None)
    except Exception as e:
        logger.debug("Wikipedia fetch failed for %s: %s", article_title, e)
        return None


def fetch_university_wikipedia(university_name: str, country: str = "") -> Optional[str]:
    """
    Try common Wikipedia article titles for a university.
    E.g. "Czech Technical University" + "Czech Republic" -> "Czech_Technical_University"
    """
    summary = fetch_wikipedia_summary(university_name)
    if summary:
        return summary
    # Try with country disambiguation
    if country:
        combined = f"{university_name} ({country})"
        summary = fetch_wikipedia_summary(combined)
        if summary:
            return summary
    return None


def fetch_exchange_rate_usd_to_eur() -> Optional[float]:
    """
    Fetch current USD to EUR rate from a free API.
    Used for cost normalization in analysis.
    Falls back to None if unavailable.
    """
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("rates", {}).get("EUR")
    except Exception as e:
        logger.debug("Exchange rate fetch failed: %s", e)
        return None
