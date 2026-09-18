import re
from typing import Any, Dict, List


def validate_business(record: Dict[str, Any]) -> tuple[bool, str]:
    name = (record.get("business_name") or "").strip()
    city = (record.get("city") or "").strip()
    country = (record.get("country") or "").strip()
    if not name:
        return False, "MALFORMED_DATA"
    if not city or not country:
        return False, "WRONG_LOCATION"
    if not re.search(r"[A-Za-z]", name):
        return False, "INVALID_BUSINESS"
    return True, "OK"


def is_valid_business(record: Dict[str, Any]) -> bool:
    ok, _ = validate_business(record)
    return ok
