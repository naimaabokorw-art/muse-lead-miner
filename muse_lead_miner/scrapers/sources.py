from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from muse_lead_miner.utils.networking import safe_get


def search_results_for(query: str, country: str = "", city: str = "", limit: int = 10, *, timeout: int = 15, max_retries: int = 1) -> List[Dict[str, Any]]:
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    response = safe_get(url, timeout=timeout, max_retries=max_retries)
    soup = BeautifulSoup(response.text or "", "html.parser")
    results = []
    for item in soup.select(".result")[:limit]:
        title_tag = item.select_one(".result__title") or item.select_one("a")
        link = item.select_one("a")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        if not title: continue
        results.append({"business_name": title, "category": "", "country": country, "region": "", "city": city, "address": "", "phone": "", "website": "", "source": "duckduckgo", "source_url": link.get("href", "") if link else "", "snippet": (item.select_one(".result__snippet").get_text(" ", strip=True) if item.select_one(".result__snippet") else "")})
    return results


def discovery_source(config: Any, logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """Discover public search results; failures are logged and return no fabricated records."""
    query = "{niche} {city} {region} {country}".format(niche=config.niche, city=config.city, region=config.region, country=config.country)
    try:
        return search_results_for(query, config.country, config.city, config.limit, timeout=config.request_timeout, max_retries=config.max_retries)
    except Exception as exc:
        if logger: logger.error("Public discovery source failed: %s", exc)
        return []
