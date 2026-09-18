from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from muse_lead_miner.utils.networking import safe_get


def _log(logger: Optional[logging.Logger], message: str, *args: Any) -> None:
    if logger:
        logger.info(message, *args)


def _parse_duckduckgo(response: Any, country: str, city: str, niche: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    soup = BeautifulSoup(response.text or "", "html.parser")
    candidates = soup.select(".result")
    parsed: List[Dict[str, Any]] = []
    rejected = 0
    for item in candidates[:limit]:
        title_tag = item.select_one(".result__title") or item.select_one("a")
        link = item.select_one("a")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        source_url = link.get("href", "").strip() if link else ""
        if not title or not source_url:
            rejected += 1
            continue
        snippet_tag = item.select_one(".result__snippet")
        parsed.append({
            "business_name": title,
            "category": niche,
            "country": country,
            "region": "",
            "city": city,
            "address": "",
            "phone": "",
            "website": "",
            "source": "duckduckgo",
            "source_url": source_url,
            "snippet": snippet_tag.get_text(" ", strip=True) if snippet_tag else "",
        })
    return parsed, len(candidates) - len(parsed) + rejected


def search_results_for(query: str, country: str = "", city: str = "", limit: int = 10, *, timeout: int = 15, max_retries: int = 1, logger: Optional[logging.Logger] = None, niche: str = "") -> List[Dict[str, Any]]:
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    _log(logger, "[DISCOVERY] Source: DuckDuckGo HTML")
    _log(logger, "[DISCOVERY] Query: %s", query)
    try:
        response = safe_get(url, timeout=timeout, max_retries=max_retries)
        _log(logger, "[DISCOVERY] HTTP status: %s", response.status_code)
        candidates = BeautifulSoup(response.text or "", "html.parser").select(".result")
        parsed, rejected = _parse_duckduckgo(response, country, city, niche, limit)
        _log(logger, "[DISCOVERY] Raw candidates: %d", len(candidates))
        _log(logger, "[DISCOVERY] Parsed candidates: %d", len(parsed))
        _log(logger, "[DISCOVERY] Rejected candidates: %d", rejected)
        if rejected:
            _log(logger, "[DISCOVERY] Rejection reason: missing result title or source URL")
        return parsed
    except Exception as exc:
        _log(logger, "[DISCOVERY] HTTP status: unavailable (%s)", exc)
        _log(logger, "[DISCOVERY] Raw candidates: 0")
        _log(logger, "[DISCOVERY] Parsed candidates: 0")
        _log(logger, "[DISCOVERY] Rejected candidates: 0")
        _log(logger, "[DISCOVERY] Rejection reason: request or parser failure: %s", exc)
        return []


def _nominatim_results(query: str, country: str, city: str, niche: str, limit: int, *, timeout: int, max_retries: int, logger: Optional[logging.Logger]) -> List[Dict[str, Any]]:
    url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit={}&q={}".format(limit, quote_plus(query))
    _log(logger, "[DISCOVERY] Source: OpenStreetMap Nominatim")
    _log(logger, "[DISCOVERY] Query: %s", query)
    try:
        response = safe_get(url, timeout=timeout, max_retries=max_retries)
        _log(logger, "[DISCOVERY] HTTP status: %s", response.status_code)
        payload = response.json()
        if not isinstance(payload, list):
            payload = []
        parsed: List[Dict[str, Any]] = []
        rejected = 0
        for item in payload:
            name = (item.get("name") or "").strip()
            source_id = item.get("osm_type") and item.get("osm_id")
            if not name or not source_id:
                rejected += 1
                continue
            parsed.append({
                "business_name": name,
                "category": niche,
                "country": country,
                "region": "",
                "city": city,
                "address": item.get("display_name", ""),
                "phone": "",
                "website": "",
                "source": "openstreetmap_nominatim",
                "source_url": f"https://www.openstreetmap.org/{item['osm_type']}/{item['osm_id']}",
                "snippet": item.get("type", "") or item.get("class", ""),
            })
        _log(logger, "[DISCOVERY] Raw candidates: %d", len(payload))
        _log(logger, "[DISCOVERY] Parsed candidates: %d", len(parsed))
        _log(logger, "[DISCOVERY] Rejected candidates: %d", rejected)
        if rejected:
            _log(logger, "[DISCOVERY] Rejection reason: missing OSM name or source identifier")
        return parsed
    except Exception as exc:
        _log(logger, "[DISCOVERY] HTTP status: unavailable (%s)", exc)
        _log(logger, "[DISCOVERY] Raw candidates: 0")
        _log(logger, "[DISCOVERY] Parsed candidates: 0")
        _log(logger, "[DISCOVERY] Rejected candidates: 0")
        _log(logger, "[DISCOVERY] Rejection reason: request or parser failure: %s", exc)
        return []


def discovery_source(config: Any, logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """Use public search, then a public OSM fallback, without fabricating records."""
    location = " ".join(part for part in (config.city, config.region, config.country) if part)
    query = f"{config.niche} {location}"
    results = search_results_for(query, config.country, config.city, config.limit, timeout=config.request_timeout, max_retries=config.max_retries, logger=logger, niche=config.niche)
    if results:
        return results[:config.limit]
    _log(logger, "[DISCOVERY] DuckDuckGo produced no parseable candidates; trying fallback")
    fallback = _nominatim_results(f"{config.niche}, {location}", config.country, config.city, config.niche, config.limit, timeout=config.request_timeout, max_retries=config.max_retries, logger=logger)
    return fallback[:config.limit]
