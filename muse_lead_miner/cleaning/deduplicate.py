from collections import defaultdict
from typing import Any, Dict, Iterable, List

from muse_lead_miner.cleaning.normalize import dedupe_key_for_business, normalize_business_record


def deduplicate_businesses(records: Iterable[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    seen: Dict[str, Dict[str, Any]] = {}
    rejected: List[Dict[str, Any]] = []
    for record in records:
        normalized = normalize_business_record(record)
        key = dedupe_key_for_business(normalized)
        if not key:
            rejected.append({**normalized, "reason_rejected": "MALFORMED_DATA"})
            continue
        existing = seen.get(key)
        if existing is None:
            seen[key] = normalized
            continue
        if len(normalized.get("website", "")) > len(existing.get("website", "")) or len(normalized.get("address", "")) > len(existing.get("address", "")):
            seen[key] = normalized
        else:
            seen[key] = existing
    return list(seen.values()), rejected


def merge_records(primary: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(primary)
    for key, value in incoming.items():
        if not merged.get(key) and value:
            merged[key] = value
    return merged
