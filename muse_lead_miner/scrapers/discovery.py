from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from muse_lead_miner.config import require_maps_api_key

BLOCKED_DOMAINS = (
    "facebook.com", "instagram.com", "tiktok.com", "linkedin.com", "yelp.com",
    "tripadvisor.com", "yellowpages.", "foursquare.com", "google.com", "bing.com",
    "duckduckgo.com", "mapquest.com", "wikipedia.org",
)


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _is_candidate_url(url: str) -> bool:
    domain = _domain(url)
    return bool(domain and not any(item in domain for item in BLOCKED_DOMAINS))


class PublicWebSearchProvider:
    """Conservative, no-key discovery using public DuckDuckGo HTML results.

    This is labelled PUBLIC_WEB_SEARCH. It is not Google Maps data and does not
    bypass blocks, execute stealth browsers, or scrape private information.
    """
    endpoint = "https://html.duckduckgo.com/html/"

    def __init__(self, timeout=15, retries=2, delay=1.0, session=None):
        self.timeout, self.retries, self.delay = timeout, retries, delay
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "MuseLeadMiner/0.1 (public research)"})

    def search(self, query: str, limit: int = 20, logger: logging.Logger | None = None) -> list[dict[str, str]]:
        last = None
        for attempt in range(max(1, self.retries)):
            try:
                response = self.session.get(self.endpoint, params={"q": query}, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text or "", "html.parser")
                results = []
                for item in soup.select(".result"):
                    link = item.select_one(".result__title a") or item.select_one("a.result__url")
                    if not link or not link.get("href"):
                        continue
                    url = link.get("href", "").strip()
                    title = link.get_text(" ", strip=True)
                    snippet_tag = item.select_one(".result__snippet")
                    snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
                    results.append({"title": title, "url": url, "snippet": snippet, "query": query})
                    if len(results) >= limit:
                        break
                return results
            except Exception as exc:
                last = exc
                if logger:
                    logger.warning("Public search unavailable for %r: %s", query, exc)
                if attempt + 1 < self.retries:
                    time.sleep(self.delay * (2 ** attempt))
        if logger and last:
            logger.warning("Public search skipped after retries: %s", last)
        return []

    def discover(self, country: str, city: str, niche: str, region: str = "", limit: int = 25, logger=None):
        location = " ".join(x for x in (city, region, country) if x).strip()
        queries = [f"{niche} in {location}", f"{niche} {location}", f'"{niche}" "{city}" businesses']
        rows, seen = [], set()
        for query in queries:
            for result in self.search(query, limit=max(limit * 2, 20), logger=logger):
                title = result["title"]
                key = (title.casefold(), result["url"].casefold())
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "business_name": title,
                    "category": niche,
                    "address": "",
                    "city": city,
                    "region": region,
                    "country": country,
                    "phone": "",
                    "website": "",
                    "website_status": "WEBSITE_STATUS_UNCERTAIN",
                    "website_source": "",
                    "website_source_url": "",
                    "maps_url": "",
                    "google_maps_url": "",
                    "google_place_id": "",
                    "rating": "",
                    "review_count": "",
                    "business_status": "",
                    "source": "PUBLIC_WEB_SEARCH",
                    "source_url": result["url"],
                    "search_snippet": result["snippet"],
                    "search_query": result["query"],
                    "source_count": 1,
                })
                if len(rows) >= limit:
                    return rows[:limit]
            time.sleep(self.delay)
        return rows[:limit]


class OpenStreetMapProvider:
    """Optional supplemental geographic source; never the default discovery source."""
    endpoint = "https://nominatim.openstreetmap.org/search"

    def __init__(self, timeout=15, retries=2, delay=1.0, session=None):
        self.timeout, self.retries, self.delay = timeout, retries, delay
        self.session = session or requests.Session()

    def discover(self, country, city, niche, region="", limit=25, logger=None):
        query = ", ".join(x for x in (niche, city, region, country) if x)
        try:
            response = self.session.get(self.endpoint, params={"q": query, "format": "jsonv2", "limit": limit}, headers={"User-Agent": "MuseLeadMiner/0.1"}, timeout=self.timeout)
            response.raise_for_status()
            return [{"business_name": x.get("name", ""), "category": niche, "address": x.get("display_name", ""), "city": city, "region": region, "country": country, "source": "OPENSTREETMAP", "source_url": f"https://www.openstreetmap.org/{x.get('osm_type', 'node')}/{x.get('osm_id', '')}", "latitude": x.get("lat", ""), "longitude": x.get("lon", ""), "website_status": "WEBSITE_STATUS_UNCERTAIN"} for x in response.json() if x.get("name")]
        except Exception as exc:
            if logger: logger.warning("Optional OpenStreetMap lookup failed: %s", exc)
            return []


class GoogleMapsProvider:
    """Optional provider retained for explicit use only; not used by default."""
    def __init__(self, *args, **kwargs):
        self.api_key = require_maps_api_key()
        if not self.api_key:
            raise RuntimeError("Google Maps provider is optional and requires GOOGLE_MAPS_API_KEY.")
        raise RuntimeError("Google Maps API provider is not the default free discovery path.")


def discovery_source(config, logger=None):
    if logger:
        logger.info("Discovery source: PUBLIC_WEB_SEARCH (no API key required)")
    return PublicWebSearchProvider(timeout=config.timeout, retries=config.retries, delay=config.delay).discover(config.country, config.city, config.niche, config.region, config.limit, logger)
