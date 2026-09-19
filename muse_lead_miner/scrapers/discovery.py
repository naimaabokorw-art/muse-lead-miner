from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from muse_lead_miner.config import require_maps_api_key


class OpenStreetMapProvider:
    """Free no-key fallback for discovery. Explicitly not Google Maps."""

    base = "https://nominatim.openstreetmap.org"

    def __init__(self, timeout: int = 15, retries: int = 3, delay: float = 0.25, session=None):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.session = session or requests.Session()

    def discover(self, country: str, city: str, niche: str, region: str = "", limit: int = 25, logger: logging.Logger | None = None):
        location = ", ".join(part for part in (city, region, country) if part)
        query = f"{niche} {location}".strip()
        rows = []
        for attempt in range(max(1, self.retries)):
            try:
                response = self.session.get(
                    f"{self.base}/search",
                    params={"q": query, "format": "jsonv2", "limit": limit},
                    headers={"User-Agent": "MuseLeadMiner/0.1 (public research)"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                for item in payload:
                    rows.append({
                        "business_name": item.get("display_name") or item.get("name") or "",
                        "category": niche,
                        "address": item.get("display_name") or "",
                        "city": city,
                        "region": region,
                        "country": country,
                        "phone": "",
                        "website": "",
                        "website_status": "WEBSITE_STATUS_UNCERTAIN",
                        "website_source": "openstreetmap_nominatim",
                        "google_maps_url": "",
                        "google_place_id": "",
                        "rating": "",
                        "review_count": "",
                        "business_status": "",
                        "opening_hours": "",
                        "latitude": item.get("lat", ""),
                        "longitude": item.get("lon", ""),
                        "source": "openstreetmap_nominatim",
                        "source_url": f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item.get('osm_id', '')}" if item.get('osm_id') else "",
                        "source_count": 1,
                    })
                if rows:
                    return rows[:limit]
            except Exception as exc:
                if logger:
                    logger.warning("OpenStreetMap fallback failed (%s)", exc)
                if attempt + 1 < self.retries:
                    time.sleep(self.delay * (2 ** attempt))
        return []


class GoogleMapsProvider:
    """Optional Google Places API provider. Requires API key; otherwise we use the free OSM fallback."""

    base = "https://maps.googleapis.com/maps/api"

    def __init__(self, api_key: str | None = None, timeout=15, retries=3, delay=.25, session=None):
        self.api_key = (api_key or require_maps_api_key()).strip()
        self.timeout, self.retries, self.delay = timeout, retries, delay
        self.session = session or requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Google Maps provider is not configured. Add GOOGLE_MAPS_API_KEY to .env.")
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
                if attempt + 1 < self.retries:
                    time.sleep(self.delay * (2 ** attempt))
        raise RuntimeError(f"Google Maps provider failed: {last}")

    def discover(self, country: str, city: str, niche: str, region: str = "", limit: int = 25, logger: logging.Logger | None = None):
        if not self.api_key:
            raise RuntimeError("Google Maps provider is not configured. Add GOOGLE_MAPS_API_KEY to .env.")
        location = ", ".join(x for x in (city, region, country) if x)
        payload = self._get("place/textsearch", {"query": f"{niche} in {location}", "language": "en"})
        rows = []
        for item in payload.get("results", [])[:limit]:
            try:
                detail = self._get("place/details", {
                    "place_id": item["place_id"],
                    "language": "en",
                    "fields": "place_id,name,types,formatted_address,address_components,formatted_phone_number,website,url,rating,user_ratings_total,business_status,opening_hours,geometry",
                }).get("result", {})
                rows.append(self._record(detail, country, city, region, niche))
            except Exception as exc:
                if logger:
                    logger.warning("Skipping Google place %s: %s", item.get("name", "unknown"), exc)
        return rows

    @staticmethod
    def _record(place, country, city, region, niche):
        components = {x.get("types", [""])[0]: x.get("long_name", "") for x in place.get("address_components", [])}
        website = place.get("website", "")
        return {
            "business_name": place.get("name", ""),
            "category": niche,
            "address": place.get("formatted_address", ""),
            "city": components.get("locality") or city,
            "region": components.get("administrative_area_level_1") or region,
            "country": components.get("country") or country,
            "phone": place.get("formatted_phone_number", ""),
            "website": website,
            "website_status": "WEBSITE_FOUND" if website else "NO_WEBSITE_CONFIRMED",
            "website_source": "google_places" if website else "google_places_explicitly_empty",
            "google_maps_url": place.get("url", ""),
            "google_place_id": place.get("place_id", ""),
            "rating": place.get("rating", ""),
            "review_count": place.get("user_ratings_total", ""),
            "business_status": place.get("business_status", ""),
            "opening_hours": "; ".join(place.get("opening_hours", {}).get("weekday_text", [])),
            "latitude": place.get("geometry", {}).get("location", {}).get("lat", ""),
            "longitude": place.get("geometry", {}).get("location", {}).get("lng", ""),
            "source": "google_maps",
            "source_url": place.get("url", ""),
            "source_count": 1,
        }


def discovery_source(config, logger=None):
    if require_maps_api_key():
        return GoogleMapsProvider(timeout=config.timeout, retries=config.retries, delay=config.delay).discover(
            config.country, config.city, config.niche, config.region, config.limit, logger
        )
    if logger:
        logger.warning("No Google Maps API key found; using OpenStreetMap Nominatim free fallback.")
    return OpenStreetMapProvider(timeout=config.timeout, retries=config.retries, delay=config.delay).discover(
        config.country, config.city, config.niche, config.region, config.limit, logger
    )
