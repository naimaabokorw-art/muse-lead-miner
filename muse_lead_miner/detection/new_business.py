from __future__ import annotations
import re

PATTERNS = ("newly opened", "just opened", "now open", "opening soon", "grand opening", "new location", "recently launched", "recently opened")

def detect_new_business(record, extra_text=""):
    evidence = []
    opening_date = record.get("new_business_date_if_known", "")
    if record.get("opening_date"): opening_date = record["opening_date"]
    for text in (extra_text, record.get("new_business_evidence", ""), record.get("snippet", ""), record.get("website_evidence", "")):
        lower = str(text or "").lower()
        evidence.extend(p for p in PATTERNS if p in lower and p not in evidence)
    if opening_date:
        return {"new_business": "TRUE", "new_business_confidence": "HIGH", "new_business_evidence": f"Opening date: {opening_date}", "new_business_source": record.get("new_business_source", "public_metadata"), "new_business_date_if_known": opening_date}
    if evidence:
        return {"new_business": "TRUE", "new_business_confidence": "MEDIUM", "new_business_evidence": "; ".join(evidence), "new_business_source": "public_text", "new_business_date_if_known": ""}
    return {"new_business": "UNCERTAIN", "new_business_confidence": "LOW", "new_business_evidence": "", "new_business_source": "", "new_business_date_if_known": ""}
