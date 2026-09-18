from typing import Any, Dict

def calculate_lead_score(record: Dict[str, Any]) -> Dict[str, Any]:
    verification = int(record.get("verification_score", 0) or 0)
    parts = {"verification": round(verification * 0.45), "website_opportunity": 15 if record.get("website_status") == "NO_OFFICIAL_WEBSITE_FOUND" else 10 if record.get("website_status") == "OFFICIAL_WEBSITE_FOUND" else 0, "public_email": 10 if record.get("email") else 0, "location": 10 if record.get("city") and record.get("country") else 0, "niche": 10 if record.get("category") else 0, "new_business": 10 if record.get("new_business") == "TRUE" else 0, "completeness": 5 if any(record.get(k) for k in ("phone", "website", "email")) else 0}
    total = min(100, max(0, sum(parts.values())))
    return {"lead_score": int(total), "score_breakdown": parts}
