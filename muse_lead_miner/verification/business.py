from typing import Any, Dict


def validate_business(record: Dict[str, Any]) -> tuple[bool, str]:
    name = (record.get("business_name") or "").strip()
    city = (record.get("city") or "").strip()
    country = (record.get("country") or "").strip()
    if not name: return False, "MALFORMED_DATA"
    if not city or not country: return False, "WRONG_LOCATION"
    if not any(ch.isalpha() for ch in name): return False, "INVALID_BUSINESS"
    return True, "OK"


def score_verification(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return deterministic verification evidence; this is confidence, not identity proof."""
    checks = (("business name present", bool(record.get("business_name")), 25), ("city present", bool(record.get("city")), 20), ("country present", bool(record.get("country")), 10), ("address present", bool(record.get("address")), 15), ("phone present", bool(record.get("phone")), 15), ("public source present", bool(record.get("source_url")), 10), ("website observed", bool(record.get("website")), 5))
    score = sum(weight for _, present, weight in checks if present)
    evidence = "; ".join(label for label, present, _ in checks if present) or "insufficient evidence"
    status = "VERIFIED" if score >= 80 else "PARTIALLY_VERIFIED" if score >= 50 else "UNCERTAIN" if score >= 25 else "REJECTED"
    return {"verification_status": status, "verification_score": score, "verification_evidence": evidence}


def is_valid_business(record: Dict[str, Any]) -> bool:
    return validate_business(record)[0]
