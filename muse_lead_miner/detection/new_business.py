from typing import Any, Dict
PATTERNS = ("grand opening", "now open", "opening soon", "new location", "just opened", "newly opened", "open for business")

def detect_new_business(record: Dict[str, Any], extra_text: str = "") -> Dict[str, Any]:
    text = " ".join((extra_text, record.get("website_evidence", ""), record.get("snippet", ""))).lower()
    matches = [p for p in PATTERNS if p in text]
    return {"new_business": "TRUE" if matches else "UNCERTAIN", "new_business_confidence": "HIGH" if matches else "LOW", "new_business_evidence": "; ".join(matches) if matches else "No public opening evidence found.", "new_business_source": record.get("source_url", "") if matches else "", "new_business_date_if_known": "UNKNOWN"}
