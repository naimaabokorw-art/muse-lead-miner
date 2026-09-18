import re
from typing import Any, Dict, List


def score_verification(record: Dict[str, Any]) -> Dict[str, Any]:
    evidence = []
    score = 0
    name_match = bool(record.get("business_name"))
    city_match = bool(record.get("city"))
    address_match = bool(record.get("address"))
    phone_match = bool(record.get("phone"))
    domain_match = bool(record.get("website"))
    if name_match:
        score += 25
        evidence.append("business name present")
    if city_match:
        score += 20
        evidence.append("city matches")
    if address_match:
        score += 20
        evidence.append("address present")
    if phone_match:
        score += 15
        evidence.append("phone present")
    if domain_match:
        score += 20
        evidence.append("website/domain observed")
    if score >= 80:
        status = "VERIFIED"
    elif score >= 50:
        status = "PARTIALLY_VERIFIED"
    elif score >= 25:
        status = "UNCERTAIN"
    else:
        status = "REJECTED"
    return {"verification_status": status, "verification_score": min(score, 100), "verification_evidence": "; ".join(evidence) or "insufficient evidence"}
