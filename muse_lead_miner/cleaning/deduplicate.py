from __future__ import annotations

from typing import Any
from muse_lead_miner.cleaning.normalize import normalize_business_record, text_key, normalize_phone


def business_key(record: dict[str, Any]) -> tuple[str, str]:
    place = str(record.get("google_place_id") or "").strip()
    if place: return ("place_id", place)
    phone = normalize_phone(record.get("phone"))
    if phone: return ("phone", phone)
    name = text_key(record.get("business_name"))
    address = text_key(record.get("address"))
    city = text_key(record.get("city"))
    return ("name_address", f"{name}|{address or city}")

def _merge(old: dict, new: dict) -> dict:
    merged = dict(old)
    for key, value in new.items():
        if not merged.get(key) and value not in (None, "", []): merged[key] = value
    urls = {str(x) for x in (old.get("source_url", ""), new.get("source_url", "")) if x}
    sources = {str(x) for x in (old.get("source", ""), new.get("source", "")) if x}
    merged["source_count"] = max(int(old.get("source_count", 1) or 1), 1) + (1 if new else 0)
    merged["duplicate_sources"] = "; ".join(sorted(sources))
    if len(urls) > 1: merged["source_urls"] = "; ".join(sorted(urls))
    return merged

def deduplicate_businesses(records):
    unique, rejected, index = [], [], {}
    for raw in records:
        record = normalize_business_record(raw)
        if not text_key(record.get("business_name")):
            rejected.append({**record, "reason_rejected": "MALFORMED_DATA"}); continue
        key = business_key(record)
        if key in index:
            position = index[key]; unique[position] = _merge(unique[position], record)
            rejected.append({**record, "reason_rejected": "DUPLICATE"})
        else:
            record.setdefault("source_count", 1); record.setdefault("duplicate_sources", record.get("source", ""))
            index[key] = len(unique); unique.append(record)
    return unique, rejected
