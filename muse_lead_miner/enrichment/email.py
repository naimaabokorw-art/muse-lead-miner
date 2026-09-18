import re
from typing import Any, Dict, List
from muse_lead_miner.utils.networking import safe_get

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GENERIC = {"info", "hello", "contact", "enquiries", "enquiry", "bookings", "admin", "office", "sales"}


def extract_emails(text: str) -> List[str]:
    return sorted(set(EMAIL_PATTERN.findall(text.lower())))


def enrich_email(record: Dict[str, Any]) -> Dict[str, Any]:
    found, source_url = [], ""
    for url in (record.get("website"), record.get("source_url")):
        if not url: continue
        try:
            response = safe_get(url, timeout=10, max_retries=1)
            found.extend(extract_emails(response.text or "")); source_url = source_url or url
        except Exception:
            continue
    email = sorted(set(found))[0] if found else ""
    if not email: return {"email":"", "email_source":"", "email_source_url":"", "email_type":"UNKNOWN", "email_confidence":"NONE", "email_status":"NO_PUBLIC_EMAIL_FOUND"}
    local = email.split("@", 1)[0].lower()
    generic = local in GENERIC or local.startswith(("info.", "hello."))
    return {"email": email, "email_source":"public page", "email_source_url":source_url, "email_type":"BUSINESS_GENERIC" if generic else "BUSINESS_OR_PERSONAL_UNCERTAIN", "email_confidence":"PUBLIC_SYNTAX_ONLY", "email_status":"PUBLIC_EMAIL_FOUND_SYNTAX_ONLY"}
