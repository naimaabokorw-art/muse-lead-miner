import re
from typing import Any, Dict

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_\.]+)", re.I),
    "facebook": re.compile(r"facebook\.com/([A-Za-z0-9_.]+)", re.I),
    "tiktok": re.compile(r"tiktok\.com/@?([A-Za-z0-9_.]+)", re.I),
    "linkedin": re.compile(r"linkedin\.com/(company|in)/([A-Za-z0-9_.-]+)", re.I),
}


def extract_socials(text: str) -> Dict[str, str]:
    socials = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(text)
        if match:
            socials[platform] = match.group(0)
    return socials


def enrich_social(record: Dict[str, Any]) -> Dict[str, Any]:
    content = ""
    for url in [record.get("website"), record.get("source_url")]:
        if url:
            try:
                from muse_lead_miner.utils.networking import safe_get

                response = safe_get(url, timeout=10, max_retries=1)
                content += (response.text or "") + "\n"
            except Exception:
                pass
    found = extract_socials(content)
    return {
        "instagram": found.get("instagram", ""),
        "facebook": found.get("facebook", ""),
        "tiktok": found.get("tiktok", ""),
        "linkedin": found.get("linkedin", ""),
    }
