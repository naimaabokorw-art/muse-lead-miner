from typing import Any, Dict

from muse_lead_miner.utils.networking import safe_get


def audit_website(record: Dict[str, Any]) -> Dict[str, Any]:
    website = record.get("website")
    if not website:
        return {"website_quality": "UNCERTAIN", "website_audit_evidence": "No website available to audit."}
    try:
        response = safe_get(website, timeout=12, max_retries=1)
        body = response.text.lower()
        title = ""
        if response.history:
            redirect = True
        else:
            redirect = False
        viewport = "viewport" in body
        contact_cta = any(term in body for term in ["contact", "book", "call", "enquire", "quote"])
        https_ok = website.startswith("https://")
        if response.status_code >= 400 or not https_ok or not viewport or not contact_cta:
            quality = "POSSIBLE_REDESIGN"
            evidence = [
                f"HTTP status {response.status_code}",
                "HTTPS unavailable" if not https_ok else "HTTPS present",
                "No mobile viewport detected" if not viewport else "Mobile viewport detected",
                "No obvious contact CTA found" if not contact_cta else "Contact CTA present",
            ]
            return {"website_quality": quality, "website_audit_evidence": "; ".join(evidence)}
        return {"website_quality": "HEALTHY", "website_audit_evidence": "Homepage responded successfully, HTTPS present, viewport found, contact path found."}
    except Exception as exc:
        return {"website_quality": "BROKEN", "website_audit_evidence": f"Website audit failed: {exc}"}
