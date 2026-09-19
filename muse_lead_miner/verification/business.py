from __future__ import annotations
from difflib import SequenceMatcher
from muse_lead_miner.cleaning.normalize import domain, text_key, normalize_phone

def identity_match(record: dict, candidate: dict) -> dict:
    score, evidence = 0, []
    if text_key(record.get("business_name")) and text_key(record.get("business_name")) == text_key(candidate.get("business_name")): score += 50; evidence.append("name")
    elif SequenceMatcher(None, text_key(record.get("business_name")), text_key(candidate.get("business_name"))).ratio() >= .8: score += 30; evidence.append("similar_name")
    if normalize_phone(record.get("phone")) and normalize_phone(record.get("phone")) == normalize_phone(candidate.get("phone")): score += 30; evidence.append("phone")
    if record.get("city") and text_key(record.get("city")) == text_key(candidate.get("city")): score += 10; evidence.append("city")
    if record.get("address") and text_key(record.get("address")) in text_key(candidate.get("address")): score += 10; evidence.append("address")
    if record.get("website") and domain(record.get("website")) == domain(candidate.get("website")): score += 10; evidence.append("domain")
    return {"identity_match_score": min(score, 100), "identity_match_evidence": "; ".join(evidence)}
