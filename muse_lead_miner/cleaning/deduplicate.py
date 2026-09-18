from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Tuple

from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.utils.networking import dedupe_norm_text, domain_from_url, normalize_phone


def _text(value: Any) -> str:
    """Create a conservative comparison key for human-entered business text."""
    if value is None:
        return ""
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    value = value.replace("&amp;", "&")
    # Apostrophes, hyphens and punctuation are separators, not identity.
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _compact_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _text(value))


def _location(record: Dict[str, Any]) -> Tuple[str, str]:
    return _text(record.get("city")), _text(record.get("country"))


def _complete(record: Dict[str, Any]) -> int:
    fields = ("business_name", "phone", "address", "website", "source_url", "category", "email")
    return sum(bool(record.get(field)) for field in fields)


def _same_business(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    left_city, left_country = _location(left)
    right_city, right_country = _location(right)
    if not left_city or not left_country or (left_city, left_country) != (right_city, right_country):
        return False

    left_phone = normalize_phone(left.get("phone", ""))
    right_phone = normalize_phone(right.get("phone", ""))
    if left_phone and right_phone and left_phone == right_phone:
        return True

    left_name = _compact_text(left.get("business_name"))
    right_name = _compact_text(right.get("business_name"))
    if left_name and right_name and left_name == right_name:
        return True

    left_domain = domain_from_url(left.get("website", ""))
    right_domain = domain_from_url(right.get("website", ""))
    return bool(left_domain and right_domain and left_domain == right_domain)


def merge_records(primary: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merge duplicate observations without overwriting useful existing evidence."""
    merged = dict(primary)
    for key, value in incoming.items():
        if not merged.get(key) and value:
            merged[key] = value
    sources = {str(value).strip() for value in (primary.get("source"), incoming.get("source")) if value}
    if len(sources) > 1:
        merged["source"] = "; ".join(sorted(sources))
    source_urls = {str(value).strip() for value in (primary.get("source_url"), incoming.get("source_url")) if value}
    if len(source_urls) > 1:
        merged["source_urls"] = "; ".join(sorted(source_urls))
    return merged


def deduplicate_businesses(records: Iterable[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Deduplicate only when location plus a strong identity signal agrees.

    Empty fields are never used as identity signals, preventing unrelated records
    with missing phones/websites from collapsing into one record.
    """
    unique: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for record in records:
        normalized = normalize_business_record(record)
        if not _compact_text(normalized.get("business_name")):
            rejected.append({**normalized, "reason_rejected": "MALFORMED_DATA"})
            continue

        duplicate_index = next((index for index, existing in enumerate(unique) if _same_business(existing, normalized)), None)
        if duplicate_index is None:
            unique.append(normalized)
            continue

        existing = unique[duplicate_index]
        # Prefer the most complete observation, with the first observation winning ties.
        if _complete(normalized) > _complete(existing):
            primary, incoming = normalized, existing
        else:
            primary, incoming = existing, normalized
        unique[duplicate_index] = merge_records(primary, incoming)
        rejected.append({**normalized, "reason_rejected": "DUPLICATE"})
    return unique, rejected
