from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import urlparse

from muse_lead_miner.cleaning.normalize import normalize_url, text_key, normalize_phone
from muse_lead_miner.scrapers.discovery import BLOCKED_DOMAINS, PublicWebSearchProvider


def _domain(url):
    return urlparse(normalize_url(url)).netloc.lower().removeprefix("www.")


def _allowed(url):
    host = _domain(url)
    return bool(host and not any(x in host for x in BLOCKED_DOMAINS))


def identity_match(record, candidate):
    score, evidence = 0, []
    left, right = text_key(record.get("business_name")), text_key(candidate.get("business_name") or candidate.get("title"))
    if left and left == right:
        score += 55; evidence.append("exact_name")
    elif left and right and SequenceMatcher(None, left, right).ratio() >= .85:
        score += 35; evidence.append("similar_name")
    text = " ".join(str(candidate.get(k, "")) for k in ("title", "snippet", "address", "city"))
    if text_key(record.get("city")) and text_key(record.get("city")) in text_key(text):
        score += 20; evidence.append("city")
    if normalize_phone(record.get("phone")) and normalize_phone(record.get("phone")) in normalize_phone(text):
        score += 25; evidence.append("phone")
    return {"identity_match_score": min(score, 100), "identity_match_evidence": "; ".join(evidence)}


def classify_website(record):
    website = normalize_url(record.get("website", ""))
    if website and _allowed(website):
        return {"website": website, "website_status": "WEBSITE_FOUND", "website_source": record.get("website_source", "input"), "website_source_url": record.get("website_source_url", record.get("source_url", ""))}
    return {"website": "", "website_status": "WEBSITE_STATUS_UNCERTAIN", "website_source": "", "website_source_url": ""}


def discover_website(record, search=None, logger=None):
    existing = classify_website(record)
    if existing["website_status"] == "WEBSITE_FOUND":
        return existing
    provider = search or PublicWebSearchProvider()
    name, city, phone, address = record.get("business_name", ""), record.get("city", ""), record.get("phone", ""), record.get("address", "")
    queries = [f'"{name}" "{city}" website', f'"{name}" "{city}" contact']
    if phone: queries.append(f'"{name}" "{phone}"')
    if address: queries.append(f'"{name}" "{address}"')
    candidates = []
    for query in queries:
        candidates.extend(provider.search(query, limit=8, logger=logger))
    best = None
    for candidate in candidates:
        url = normalize_url(candidate.get("url", ""))
        if not _allowed(url):
            continue
        match = identity_match(record, candidate)
        if match["identity_match_score"] >= 75 and (best is None or match["identity_match_score"] > best[0]):
            best = (match["identity_match_score"], url, candidate, match)
    if best:
        _, url, candidate, match = best
        return {"website": url, "website_status": "WEBSITE_FOUND", "website_source": "PUBLIC_WEB_SEARCH", "website_source_url": candidate.get("url", ""), **match}
    return {"website": "", "website_status": "NO_WEBSITE_FOUND_AFTER_SEARCH", "website_source": "PUBLIC_WEB_SEARCH", "website_source_url": "", "identity_match_score": 0, "identity_match_evidence": "No strong official-domain match found in public searches."}
