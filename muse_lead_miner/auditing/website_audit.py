import re
from typing import Any, Dict

NEW_BUSINESS_PATTERNS = [
    "grand opening",
    "now open",
    "opening soon",
    "new location",
    "just opened",
    "newly opened",
    "open for business",
    "we are open",
]


def detect_new_business(record: Dict[str, Any], extra_text: str = "") -> Dict[str, Any]:
    text = (extra_text or "") + " " + (record.get("website") or "") + " " + (record.get("source_url") or "")
    lowered = text.lower()
    matches = [p for p in NEW_BUSINESS_PATTERNS if p in lowered]
    if matches:
        return {
            "new_business": "TRUE",
            "new_business_confidence": "HIGH",
            "new_business_evidence": "; ".join(matches),
            "new_business_source": record.get("source") or "public listing",
            "new_business_date_if_known": "UNKNOWN",
        }
    return {
        "new_business": "UNCERTAIN",
        "new_business_confidence": "LOW",
        "new_business_evidence": "No strong public evidence of opening date or launch announcement was found.",
        "new_business_source": "",
        "new_business_date_if_known": "UNKNOWN",
    }
