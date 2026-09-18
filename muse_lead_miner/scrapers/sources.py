import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from muse_lead_miner.utils.networking import safe_get


def search_results_for(query: str, country: str = "", city: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    url = "https://html.duckduckgo.com/html/?q=" + query.replace(" ", "+")
    try:
        response = safe_get(url, timeout=15, max_retries=1)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return []
    results: List[Dict[str, Any]] = []
    for item in soup.select(".result")[:limit]:
        title_tag = item.select_one(".result__title") or item.select_one("a")
        snippet = item.select_one(".result__snippet")
        url_tag = item.select_one("a")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        source_url = url_tag.get("href") if url_tag else ""
        if not title:
            continue
        results.append({
            "business_name": title,
            "category": "",
            "country": country,
            "region": "",
            "city": city,
            "address": "",
            "phone": "",
            "website": "",
            "source": "duckduckgo",
            "source_url": source_url,
            "snippet": snippet.get_text(" ", strip=True) if snippet else "",
        })
    return results
