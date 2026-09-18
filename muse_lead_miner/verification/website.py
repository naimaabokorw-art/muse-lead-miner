from typing import Any, Dict
from muse_lead_miner.utils.networking import domain_from_url, normalize_url


def discover_website(record: Dict[str, Any]) -> Dict[str, Any]:
    website = normalize_url(record.get("website", ""))
    source = normalize_url(record.get("source_url", ""))
    source_domain = domain_from_url(source)
    directory_domains = ("duckduckgo.com", "google.", "facebook.com", "instagram.com", "linkedin.com", "yelp.")
    if website and not any(d in domain_from_url(website) for d in directory_domains):
        return {"website": website, "website_status": "OFFICIAL_WEBSITE_FOUND", "website_evidence": f"Official-domain candidate observed in public record: {website}."}
    if source and source_domain and not any(d in source_domain for d in directory_domains):
        return {"website": source, "website_status": "OFFICIAL_WEBSITE_FOUND", "website_evidence": f"Non-directory public source domain observed: {source_domain}."}
    return {"website": "", "website_status": "NO_OFFICIAL_WEBSITE_FOUND", "website_evidence": "No credible official domain was found in the available public result."}
