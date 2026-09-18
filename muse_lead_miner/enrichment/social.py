import re
from typing import Any, Dict
from muse_lead_miner.utils.networking import safe_get
PATTERNS = {"instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]+)", re.I), "facebook": re.compile(r"facebook\.com/([A-Za-z0-9_.]+)", re.I), "tiktok": re.compile(r"tiktok\.com/@?([A-Za-z0-9_.]+)", re.I), "linkedin": re.compile(r"linkedin\.com/(?:company|in)/([A-Za-z0-9_.-]+)", re.I)}

def enrich_social(record: Dict[str, Any]) -> Dict[str, Any]:
    text = ""
    for url in (record.get("website"), record.get("source_url")):
        if url:
            try: text += (safe_get(url, timeout=10, max_retries=1).text or "")
            except Exception: continue
    return {name: (match.group(0) if (match := pattern.search(text)) else "") for name, pattern in PATTERNS.items()}
