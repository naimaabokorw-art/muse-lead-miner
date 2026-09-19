from __future__ import annotations

import logging
import time
from typing import Any
import requests
from muse_lead_miner.config import require_maps_api_key

class OpenStreetMapProvider:
    """Free, no-key fallback. Results are explicitly marked as OpenStreetMap data."""
    base = "https://nominatim.openstreetmap.org"
    def __init__(self, timeout=15, retries=3, delay=.25, session=None):
        self.timeout, self.retries, self.delay = timeout, retries, delay
        self.session = session or requests.Session()

    def discover(self, country, city, niche, region="", limit=25, logger=None):
        location = ", ".join(x for x in (city, region, country) if x)
        query = f"{niche} {location}".strip()
        for attempt in range(max(1, self.retries)):
            try:
                response = self.session.get(
                    f"{self.base}/search",
                    params={"q": query, "format": "jsonv2", "limit": limit},
                    headers={"User-Agent": "MuseLeadMiner/0.1 (public research)"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                rows = []
                for item in response.json():
                    osm_url = ""
                    if item.get("osm_id"):
                        osm_url = f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item['osm_id']}"
                    rows.append({
                        "business_name": item.get("name") or item.get("display_name", ""),
                        "category": niche, "address": item.get("display_name", ""),
                        "city": city, "region": region, "country": country, "phone": "", "website": "",
                        "website_status": "WEBSITE_STATUS_UNCERTAIN", "website_source": "openstreetmap_nominatim",
                        "google_maps_url": "", "google_place_id": "", "rating": "", "review_count": "",
                        "business_status": "", "opening_hours": "", "latitude": item.get("lat", ""),
                        "longitude": item.get("lon", ""), "source": "openstreetmap_nominatim",
                        "source_url": osm_url, "source_count": 1,
                    })
                return rows[:limit]
            except Exception as exc:
                if logger: logger.warning("OpenStreetMap fallback failed: %s", exc)
                if attempt + 1 < self.retries: time.sleep(self.delay * (2 ** attempt))
        return []

class GoogleMapsProvider:
    """Optional Google Places provider; never scrapes Maps HTML."""
    base = "https://maps.googleapis.com/maps/api"
    def __init__(self, api_key=None, timeout=15, retries=3, delay=.25, session=None):
        self.api_key = (api_key or require_maps_api_key()).strip()
        self.timeout, self.retries, self.delay = timeout, retries, delay
        self.session = session or requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Google Maps provider is not configured. Add GOOGLE_MAPS_API_KEY to .env, or use the free OpenStreetMap fallback.")
        params = {**params, "key": self.api_key}
        last = None
        for attempt in range(max(1, self.retries)):
            try:
                response = self.session.get(f"{self.base}/{endpoint}/json", params=params, timeout=self.timeout)
                response.raise_for_status(); payload = response.json()
                if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
                    raise RuntimeError(f"Google Places API error: {payload.get('status')} {payload.get('error_message', '')}".strip())
                return payload
            except Exception as exc:
                last = exc
                if attempt + 1 < self.retries: time.sleep(self.delay * (2 ** attempt))
        raise RuntimeError(f"Google Maps provider failed: {last}")

    def discover(self, country, city, niche, region="", limit=25, logger=None):
        location = ", ".join(x for x in (city, region, country) if x)
        payload = self._get("place/textsearch", {"query": f"{niche} in {location}", "language": "en"})
        rows = []
        for item in payload.get("results", [])[:limit]:
            try:
                detail = self._get("place/details", {"place_id": item["place_id"], "language": "en", "fields": "place_id,name,formatted_address,address_components,formatted_phone_number,website,url,rating,user_ratings_total,business_status,opening_hours,geometry"}).get("result", {})
                rows.append(self._record(detail, country, city, region, niche))
            except Exception as exc:
                if logger: logger.warning("Skipping Google place %s: %s", item.get("name", "unknown"), exc)
        return rows

    @staticmethod
    def _record(place, country, city, region, niche):
        components = {x.get("types", [""])[0]: x.get("long_name", "") for x in place.get("address_components", [])}
        website = place.get("website", "")
        return {"business_name": place.get("name", ""), "category": niche, "address": place.get("formatted_address", ""), "city": components.get("locality") or city, "region": components.get("administrative_area_level_1") or region, "country": components.get("country") or country, "phone": place.get("formatted_phone_number", ""), "website": website, "website_status": "WEBSITE_FOUND" if website else "NO_WEBSITE_CONFIRMED", "website_source": "google_places" if website else "google_places_explicitly_empty", "google_maps_url": place.get("url", ""), "google_place_id": place.get("place_id", ""), "rating": place.get("rating", ""), "review_count": place.get("user_ratings_total", ""), "business_status": place.get("business_status", ""), "opening_hours": "; ".join(place.get("opening_hours", {}).get("weekday_text", [])), "latitude": place.get("geometry", {}).get("location", {}).get("lat", ""), "longitude": place.get("geometry", {}).get("location", {}).get("lng", ""), "source": "google_maps", "source_url": place.get("url", ""), "source_count": 1}

def discovery_source(config, logger=None):
    if require_maps_api_key():
        return GoogleMapsProvider(timeout=config.timeout, retries=config.retries, delay=config.delay).discover(config.country, config.city, config.niche, config.region, config.limit, logger)
    if logger: logger.warning("GOOGLE_MAPS_API_KEY is not set; using free OpenStreetMap Nominatim discovery. This is not Google Maps data.")
    return OpenStreetMapProvider(timeout=config.timeout, retries=config.retries, delay=config.delay).discover(config.country, config.city, config.niche, config.region, config.limit, logger)
