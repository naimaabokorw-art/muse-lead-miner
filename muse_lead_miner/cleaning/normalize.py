import re
from typing import Any, Dict, List

from muse_lead_miner.utils.networking import domain_from_url, normalize_name, normalize_phone, normalize_url


def normalize_business_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    normalized["business_name"] = normalize_name(record.get("business_name", ""))
    normalized["country"] = (record.get("country") or "").strip()
    normalized["region"] = (record.get("region") or "").strip()
    normalized["city"] = (record.get("city") or "").strip()
    normalized["category"] = (record.get("category") or "").strip()
    normalized["address"] = (record.get("address") or "").strip()
    normalized["source"] = (record.get("source") or "").strip()
    normalized["source_url"] = normalize_url(record.get("source_url", ""))
    normalized["website"] = normalize_url(record.get("website", ""))
    normalized["phone"] = normalize_phone(record.get("phone", ""))
    return normalized


def normalize_email(value: str) -> str:
    if not value:
        return ""
    return value.strip().lower()


def normalize_domain(value: str) -> str:
    return domain_from_url(value)


def dedupe_key_for_business(record: Dict[str, Any]) -> str:
    name = normalize_name(record.get("business_name", ""))
    phone = normalize_phone(record.get("phone", ""))
    domain = normalize_domain(record.get("website", "")) or normalize_domain(record.get("source_url", ""))
    address = (record.get("address") or "").lower()
    city = (record.get("city") or "").lower()
    country = (record.get("country") or "").lower()
    parts = [name.lower(), phone, domain, address, city, country]
    return "|".join(parts)


def normalization_tests():
    return [
        ({"business_name": "Joe's Barber Shop", "phone": "(02) 555-1234", "website": "https://joesbarbershop.com/"}, {"phone": "025551234"}),
        ({"source_url": "//example.com/page"}, {"source_url": "https://example.com/page"}),
    ]
