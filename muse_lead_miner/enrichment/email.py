from __future__ import annotations

import re
from collections.abc import Callable
from muse_lead_miner.cleaning.normalize import domain, text_key
from muse_lead_miner.utils.networking import safe_get

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
GENERIC = {"info", "hello", "contact", "office", "sales", "bookings", "enquiries", "enquiry", "admin"}

def extract_emails(text: str):
    return sorted({x.lower() for x in EMAIL_PATTERN.findall(text or "")})

def email_confidence(email, record, url):
    if domain(url) and email.rsplit("@", 1)[-1].lower() == domain(url): return "HIGH"
    return "MEDIUM" if record.get("business_name") else "LOW"

def enrich_email(record: dict, fetch: Callable = safe_get):
    website = record.get("website", "")
    if not website:
        return {"email": "", "email_source": "", "email_source_url": "", "email_type": "UNKNOWN", "email_confidence": "NONE", "email_status": "NO_PUBLIC_EMAIL_FOUND"}
    candidates = [website.rstrip("/") + path for path in ("/contact", "/about")]
    candidates.insert(0, website)
    for url in candidates:
        try:
            response = fetch(url, timeout=15, max_retries=2)
            for email in extract_emails(response.text):
                local = email.split("@", 1)[0]
                return {"email": email, "email_source": "official_website", "email_source_url": url,
                    "email_type": "BUSINESS_GENERIC" if local in GENERIC else "BUSINESS_ADDRESS_PUBLIC",
                    "email_confidence": email_confidence(email, record, website), "email_status": "PUBLIC_EMAIL_FOUND_UNVERIFIED"}
        except Exception:
            continue
    return {"email": "", "email_source": "", "email_source_url": "", "email_type": "UNKNOWN", "email_confidence": "NONE", "email_status": "NO_PUBLIC_EMAIL_FOUND"}
