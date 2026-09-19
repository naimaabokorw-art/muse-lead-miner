from __future__ import annotations

import re
from collections.abc import Callable
from muse_lead_miner.cleaning.normalize import domain
from muse_lead_miner.utils.networking import safe_get

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
GENERIC = {"info", "hello", "contact", "office", "sales", "bookings", "enquiries", "enquiry", "admin"}

def extract_emails(text):
    return sorted({x.lower() for x in EMAIL_PATTERN.findall(text or "")})

def _result(email, source, url, confidence):
    local = email.split("@", 1)[0].lower()
    return {"email": email, "email_source": source, "email_source_url": url, "email_type": "BUSINESS_GENERIC" if local in GENERIC else "BUSINESS_NAMED" if local and "." in local else "UNKNOWN", "email_confidence": confidence, "email_status": "PUBLIC_EMAIL_FOUND_UNVERIFIED"}

def enrich_email(record: dict, fetch: Callable = safe_get):
    website = record.get("website", "")
    if not website:
        return {"email": "", "email_source": "", "email_source_url": "", "email_type": "UNKNOWN", "email_confidence": "NONE", "email_status": "NO_PUBLIC_EMAIL_FOUND"}
    base = website.rstrip("/")
    for url in (base, base + "/contact", base + "/about"):
        try:
            response = fetch(url, timeout=15, max_retries=2)
            for email in extract_emails(getattr(response, "text", "")):
                confidence = "HIGH" if domain(url) == email.rsplit("@", 1)[-1].lower() else "MEDIUM"
                return _result(email, "official_website", url, confidence)
        except Exception:
            continue
    return {"email": "", "email_source": "", "email_source_url": "", "email_type": "UNKNOWN", "email_confidence": "NONE", "email_status": "NO_PUBLIC_EMAIL_FOUND"}
