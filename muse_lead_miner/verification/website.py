from __future__ import annotations
from muse_lead_miner.cleaning.normalize import normalize_url, domain
from muse_lead_miner.verification.business import identity_match

def classify_website(record):
    website = normalize_url(record.get("website", ""))
    if website: return {"website": website, "website_status": "WEBSITE_FOUND", "website_source": record.get("website_source", "google_maps")}
    if record.get("website_status") == "NO_WEBSITE_CONFIRMED": return {"website": "", "website_status": "NO_WEBSITE_CONFIRMED", "website_source": record.get("website_source", "google_maps_explicitly_empty")}
    return {"website": "", "website_status": "WEBSITE_STATUS_UNCERTAIN", "website_source": ""}

def discover_website(record, candidate=None):
    if not candidate: return classify_website(record)
    match = identity_match(record, candidate)
    if match["identity_match_score"] >= 70 and domain(candidate.get("website")):
        return {**match, "website": normalize_url(candidate["website"]), "website_status": "WEBSITE_FOUND", "website_source": "website_verification"}
    return {**match, "website": "", "website_status": "WEBSITE_STATUS_UNCERTAIN", "website_source": ""}
