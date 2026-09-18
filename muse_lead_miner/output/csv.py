from typing import Any, Dict


def calculate_lead_score(record: Dict[str, Any]) -> Dict[str, Any]:
    verification = record.get("verification_score", 0)
    website_score = 0
    if record.get("website_status") == "NO_OFFICIAL_WEBSITE_FOUND":
        website_score = 15
    elif record.get("website_status") in {"OFFICIAL_WEBSITE_FOUND", "SOCIAL_ONLY"}:
        website_score = 10
    elif record.get("website_status") == "WEBSITE_BROKEN":
        website_score = 5
    email_score = 10 if record.get("email") else 0
    location_score = 10 if record.get("city") and record.get("country") else 0
    niche_score = 10 if record.get("category") else 0
    new_business_score = 10 if record.get("new_business") == "TRUE" else 0
    completeness = 5 if record.get("website") or record.get("email") or record.get("phone") else 0
    raw_score = verification * 0.45 + website_score + email_score + location_score + niche_score + new_business_score + completeness
    final_score = int(min(100, max(0, round(raw_score))))
    breakdown = {
        "verification": verification,
        "website": website_score,
        "email": email_score,
        "location": location_score,
        "niche": niche_score,
        "new_business": new_business_score,
        "completeness": completeness,
    }
    return {"lead_score": final_score, "score_breakdown": breakdown}
