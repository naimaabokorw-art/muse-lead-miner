from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse


def text_key(value: Any) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)

def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("&amp;", "&")).strip()

def normalize_phone(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))

def normalize_url(value: Any) -> str:
    value = str(value or "").strip()
    if not value: return ""
    if value.startswith("//"): value = "https:" + value
    if not value.startswith(("http://", "https://")): value = "https://" + value
    parsed = urlparse(value)
    return parsed.geturl().rstrip("/") if parsed.netloc else ""

def domain(value: Any) -> str:
    return urlparse(normalize_url(value)).netloc.lower().removeprefix("www.")

def normalize_business_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    for key in ("business_name", "category", "address", "city", "region", "country", "source", "source_url"):
        result[key] = normalize_name(record.get(key, ""))
    result["website"] = normalize_url(record.get("website", ""))
    result["phone"] = normalize_phone(record.get("phone", ""))
    result["google_maps_url"] = normalize_url(record.get("google_maps_url", ""))
    return result
