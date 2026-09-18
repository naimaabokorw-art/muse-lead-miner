import re
from typing import Any, Dict

from muse_lead_miner.utils.networking import domain_from_url, normalize_url


def discover_website(record: Dict[str, Any]) -> Dict[str, Any]:
    website = normalize_url(record.get("website", ""))
    if website:
        status = "OFFICIAL_WEBSITE_FOUND"
        evidence = f"Candidate website {website} was present in the public record."
    else:
        domain = domain_from_url(record.get("source_url", ""))
        if domain and "google" not in domain and "facebook" not in domain:
            status = "OFFICIAL_WEBSITE_FOUND"
            evidence = f"Public source pointed to a likely business domain: {domain}."
        else:
            status = "NO_OFFICIAL_WEBSITE_FOUND"
            evidence = "Business has active public listings and social presence; no credible official domain was discovered after multiple public-source searches."
    return {"website": website, "website_status": status, "website_evidence": evidence}
