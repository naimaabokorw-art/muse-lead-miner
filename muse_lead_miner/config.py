from __future__ import annotations

import os
from dataclasses import dataclass

VALID_MODES = {"no_website", "new_business", "all", "email_enrichment"}
OUTPUT_FIELDS = [
    "business_name", "category", "address", "city", "region", "country", "phone",
    "website", "website_status", "website_source", "website_source_url", "maps_url",
    "google_maps_url", "google_place_id", "rating", "review_count", "business_status",
    "opening_hours", "latitude", "longitude", "new_business", "new_business_confidence",
    "new_business_evidence", "new_business_source", "new_business_date_if_known", "email",
    "email_source", "email_source_url", "email_type", "email_confidence", "email_status",
    "identity_match_score", "identity_match_evidence", "lead_category", "source", "source_url",
    "date_found", "source_count", "duplicate_sources",
]

@dataclass
class MuseConfig:
    country: str = ""
    city: str = ""
    region: str = ""
    niche: str = ""
    limit: int = 25
    mode: str = "all"
    input_path: str = ""
    output_directory: str = "data/runs"
    website_verification_enabled: bool = True
    timeout: int = 15
    retries: int = 2
    delay: float = 1.0

    @classmethod
    def from_args(cls, args):
        return cls(country=args.country, city=args.city, region=args.region, niche=args.niche,
                   limit=args.limit, mode=args.mode, input_path=args.input or "",
                   output_directory=args.output_directory, website_verification_enabled=True,
                   timeout=args.timeout, retries=args.retries, delay=args.delay)

def maps_api_key() -> str:
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

def require_maps_api_key() -> str:
    return maps_api_key()
