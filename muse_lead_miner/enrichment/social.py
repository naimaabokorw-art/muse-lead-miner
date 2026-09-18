import re
from typing import Any, Dict, List

from muse_lead_miner.utils.networking import safe_get

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_emails(text: str) -> List[str]:
    return sorted(set(EMAIL_PATTERN.findall(text.lower())))


def enrich_email(record: Dict[str, Any]) -> Dict[str, Any]:
    emails = []
    for url in [record.get("website"), record.get("source_url")]:
        if not url:
            continue
        try:
            response = safe_get(url, timeout=10, max_retries=1)
            emails.extend(extract_emails(response.text or ""))
        except Exception:
            pass
    email = emails[0] if emails else ""
    return {
        "email": email,
        "email_source": "public website" if email else "",
        "email_source_url": record.get("website") or record.get("source_url") or "",
        "email_type": "BUSINESS_GENERIC" if email else "UNCERTAIN",
        "email_confidence": "HIGH" if email else "LOW",
        "email_status": "PUBLIC_EMAIL_FOUND" if email else "NO_PUBLIC_EMAIL_FOUND",
    }
