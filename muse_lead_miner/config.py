from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_COUNTRY = "Australia"
DEFAULT_REGION = ""
DEFAULT_CITY = "Sydney"
DEFAULT_NICHE = "beauty salon"
DEFAULT_LIMIT = 25
DEFAULT_MODE = "all"
OUTPUT_DIRECTORY = "data/runs"
MIN_LEAD_SCORE = 40
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
REQUEST_DELAY = 0.8
MAX_CONCURRENT_REQUESTS = 4
SUPPORTED_COUNTRIES = {
    "United States": {"aliases": ["USA", "US", "United States", "United States of America"]},
    "United Kingdom": {"aliases": ["UK", "United Kingdom", "England", "Scotland", "Wales", "Northern Ireland"]},
    "Australia": {"aliases": ["AU", "AUS", "Australia"]},
    "Canada": {"aliases": ["CA", "Canada"]},
    "Ireland": {"aliases": ["IE", "Ireland"]},
    "New Zealand": {"aliases": ["NZ", "New Zealand"]},
    "United Arab Emirates": {"aliases": ["UAE", "United Arab Emirates", "Dubai", "Abu Dhabi"]},
    "Saudi Arabia": {"aliases": ["SA", "Saudi Arabia"]},
    "Qatar": {"aliases": ["QA", "Qatar"]},
    "Kuwait": {"aliases": ["KW", "Kuwait"]},
    "Netherlands": {"aliases": ["NL", "The Netherlands", "Netherlands"]},
    "Germany": {"aliases": ["DE", "Germany"]},
    "Switzerland": {"aliases": ["CH", "Switzerland"]},
}

NICHE_DATABASE = [
    "beauty salon",
    "hair salon",
    "barber",
    "nail salon",
    "lash studio",
    "makeup artist",
    "aesthetic clinic",
    "med spa",
    "physiotherapist",
    "chiropractor",
    "dentist",
    "personal trainer",
    "gym",
    "Pilates studio",
    "yoga studio",
    "wellness business",
    "tutor",
    "tutoring center",
    "private school",
    "training academy",
    "music teacher",
    "driving school",
    "course provider",
    "consultant",
    "accountant",
    "small law firm",
    "insurance broker",
    "business coach",
    "career coach",
    "real estate agent",
    "property manager",
    "photographer",
    "wedding photographer",
    "videographer",
    "event planner",
    "wedding planner",
    "interior designer",
    "architect",
    "cleaner",
    "landscaper",
    "renovation company",
    "electrician",
    "plumber",
    "auto detailing",
    "auto repair",
    "mobile mechanic",
    "pet groomer",
    "dog trainer",
    "florist",
    "bakery",
    "caterer",
    "cafe",
    "restaurant",
]

VALID_MODES = {"no_website", "new_business", "redesign", "all"}


@dataclass
class MuseConfig:
    country: str = DEFAULT_COUNTRY
    region: str = DEFAULT_REGION
    city: str = DEFAULT_CITY
    niche: str = DEFAULT_NICHE
    limit: int = DEFAULT_LIMIT
    mode: str = DEFAULT_MODE
    output_directory: str = OUTPUT_DIRECTORY
    min_lead_score: int = MIN_LEAD_SCORE
    request_timeout: int = REQUEST_TIMEOUT
    max_retries: int = MAX_RETRIES
    request_delay: float = REQUEST_DELAY
    max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS
    resume: bool = False
    campaign_file: str | None = None

    @classmethod
    def from_args(cls, args: Any) -> "MuseConfig":
        return cls(
            country=args.country or DEFAULT_COUNTRY,
            region=getattr(args, "state", None) or getattr(args, "region", "") or DEFAULT_REGION,
            city=args.city or DEFAULT_CITY,
            niche=args.niche or DEFAULT_NICHE,
            limit=int(args.limit or DEFAULT_LIMIT),
            mode=args.mode or DEFAULT_MODE,
            output_directory=args.output_directory or OUTPUT_DIRECTORY,
            min_lead_score=int(args.min_lead_score or MIN_LEAD_SCORE),
            request_timeout=int(args.request_timeout or REQUEST_TIMEOUT),
            max_retries=int(args.max_retries or MAX_RETRIES),
            request_delay=float(args.request_delay or REQUEST_DELAY),
            max_concurrent_requests=int(args.max_concurrent_requests or MAX_CONCURRENT_REQUESTS),
            resume=bool(getattr(args, "resume", False)),
            campaign_file=getattr(args, "campaign", None),
        )

    @property
    def run_folder_name(self) -> str:
        from datetime import datetime

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        safe_country = self.country.replace(" ", "_")
        safe_city = self.city.replace(" ", "_")
        safe_niche = self.niche.replace(" ", "_")
        return f"{stamp}_{safe_country}_{safe_city}_{safe_niche}"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "country": self.country,
            "region": self.region,
            "city": self.city,
            "niche": self.niche,
            "limit": self.limit,
            "mode": self.mode,
            "output_directory": self.output_directory,
            "min_lead_score": self.min_lead_score,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "request_delay": self.request_delay,
            "max_concurrent_requests": self.max_concurrent_requests,
        }


def ensure_project_paths(root: Path | str) -> Dict[str, Path]:
    root_path = Path(root)
    paths = {
        "root": root_path,
        "data": root_path / "data",
        "runs": root_path / OUTPUT_DIRECTORY,
        "logs": root_path / "logs",
        "tests": root_path / "tests",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
