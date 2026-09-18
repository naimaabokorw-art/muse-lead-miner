from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from muse_lead_miner.utils.networking import safe_get


def build_discovery_queries(country: str, region: str, city: str, niche: str) -> List[str]:
    """Build broad, localized public-search queries without requiring a website."""
    location = " ".join(part.strip() for part in (city, region, country) if part and part.strip())
    short_location = " ".join(part.strip() for part in (city, country) if part and part.strip())
    return list(dict.fromkeys([
        f"{niche} {location}",
        f"{niche}s {short_location}",
        f"{niche} {city} business directory",
        f"{niche} {city} local directory",
    ]))


def _log(logger: Optional[logging.Logger], message: str, *args: Any) -> None:
    if logger:
        logger.info(message, *args)


def _candidate(name: str, url: str, country: str, region: str, city: str, niche: str, source: str, snippet: str = "", address: str = "") -> Dict[str, Any]:
    return {
        "business_name": name,
        "category": niche,
        "country": country,
        "region": region,
        "city": city,
        "address": address,
        "phone": "",
        "website": "",
        "source": source,
        "source_url": url,
        "snippet": snippet,
    }


def parse_duckduckgo_response(response: Any, country: str, region: str, city: str, niche: str, source: str = "duckduckgo") -> Tuple[List[Dict[str, Any]], int]:
    soup = BeautifulSoup(response.text or "", "html.parser")
    items = soup.select(".result")
    parsed: List[Dict[str, Any]] = []
    rejected = 0
    for item in items:
        title_tag = item.select_one(".result__title") or item.select_one("a")
        link = item.select_one(".result__title a") or item.select_one("a")
        name = title_tag.get_text(" ", strip=True) if title_tag else ""
        url = (link.get("href", "") if link else "").strip()
        snippet_tag = item.select_one(".result__snippet")
        if not name or not url:
            rejected += 1
            continue
        parsed.append(_candidate(name, url, country, region, city, niche, source, snippet_tag.get_text(" ", strip=True) if snippet_tag else ""))
    return parsed, rejected


def search_results_for(query: str, country: str = "", city: str = "", limit: int = 10, *, timeout: int = 15, max_retries: int = 1, logger: Optional[logging.Logger] = None, niche: str = "", region: str = "") -> List[Dict[str, Any]]:
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    _log(logger, "[DISCOVERY] Source: DuckDuckGo HTML")
    _log(logger, "[DISCOVERY] Query: %s", query)
    try:
        response = safe_get(url, timeout=timeout, max_retries=max_retries)
        parsed, rejected = parse_duckduckgo_response(response, country, region, city, niche)
        _log(logger, "[DISCOVERY] HTTP status: %s", response.status_code)
        _log(logger, "[DISCOVERY] Raw candidates: %d", len(BeautifulSoup(response.text or "", "html.parser").select(".result")))
        _log(logger, "[DISCOVERY] Parsed candidates: %d", len(parsed))
        _log(logger, "[DISCOVERY] Rejected candidates: %d", rejected)
        if rejected:
            _log(logger, "[DISCOVERY] Rejection reason: missing title or source URL")
        return parsed[:limit]
    except Exception as exc:
        _log(logger, "[DISCOVERY] BLOCKED/UNAVAILABLE: DuckDuckGo (%s)", exc)
        return []


def _nominatim_results(query: str, country: str, region: str, city: str, niche: str, limit: int, *, timeout: int, max_retries: int, logger: Optional[logging.Logger]) -> List[Dict[str, Any]]:
    url = f"https://nominatim.openstreetmap.org/search?format=jsonv2&limit={limit}&q={quote_plus(query)}"
    _log(logger, "[DISCOVERY] Source: OpenStreetMap Nominatim")
    _log(logger, "[DISCOVERY] Query: %s", query)
    try:
        response = safe_get(url, timeout=timeout, max_retries=max_retries)
        payload = response.json()
        payload = payload if isinstance(payload, list) else []
        parsed = []
        rejected = 0
        for item in payload:
            name = str(item.get("name") or "").strip()
            osm_type, osm_id = item.get("osm_type"), item.get("osm_id")
            if not name or not osm_type or not osm_id:
                rejected += 1
                continue
            parsed.append(_candidate(name, f"https://www.openstreetmap.org/{osm_type}/{osm_id}", country, region, city, niche, "openstreetmap_nominatim", str(item.get("type") or item.get("class") or ""), str(item.get("display_name") or "")))
        _log(logger, "[DISCOVERY] HTTP status: %s", response.status_code)
        _log(logger, "[DISCOVERY] Raw candidates: %d", len(payload))
        _log(logger, "[DISCOVERY] Parsed candidates: %d", len(parsed))
        _log(logger, "[DISCOVERY] Rejected candidates: %d", rejected)
        return parsed
    except Exception as exc:
        _log(logger, "[DISCOVERY] BLOCKED/UNAVAILABLE: OpenStreetMap Nominatim (%s)", exc)
        return []


def discovery_source(config: Any, logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """Query independent public sources and return raw, usable candidates only."""
    target = max(int(config.limit), 1)
    fetch_limit = max(target * 3, 20)
    queries = build_discovery_queries(config.country, config.region, config.city, config.niche)
    all_results: List[Dict[str, Any]] = []
    for query in queries:
        results = search_results_for(query, config.country, config.city, fetch_limit, timeout=config.request_timeout, max_retries=config.max_retries, logger=logger, niche=config.niche, region=config.region)
        all_results.extend(results)
        if len(all_results) >= fetch_limit:
            break

    if not all_results:
        _log(logger, "[DISCOVERY] Trying fallback source: OpenStreetMap Nominatim")
        for query in (f"{config.niche}, {config.city}, {config.country}", f"{config.niche}, {config.city}"):
            all_results.extend(_nominatim_results(query, config.country, config.region, config.city, config.niche, fetch_limit, timeout=config.request_timeout, max_retries=config.max_retries, logger=logger))
            if len(all_results) >= fetch_limit:
                break

    # Preserve source evidence and remove exact duplicate URLs/names before returning.
    unique: List[Dict[str, Any]] = []
    seen = set()
    for record in all_results:
        key = (record.get("source_url", "").lower(), record.get("business_name", "").casefold())
        if not key[0] and not key[1] or key in seen:
            continue
        seen.add(key)
        unique.append(record)
    _log(logger, "[DISCOVERY] Usable candidates: %d", len(unique))
    return unique
