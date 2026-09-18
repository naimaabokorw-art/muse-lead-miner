from typing import Any, Dict
from muse_lead_miner.utils.networking import safe_get

def audit_website(record: Dict[str, Any]) -> Dict[str, Any]:
    website = record.get("website")
    if not website: return {"website_quality":"NOT_AUDITABLE", "website_audit_evidence":"No website available to audit."}
    try:
        response = safe_get(website, timeout=12, max_retries=1); body = (response.text or "").lower()
        issues = []
        if response.status_code >= 400: issues.append(f"HTTP status {response.status_code}")
        if not website.startswith("https://"): issues.append("HTTPS unavailable")
        if "viewport" not in body: issues.append("mobile viewport not detected")
        if not any(x in body for x in ("contact", "book", "call", "enquire", "quote")): issues.append("no obvious contact CTA")
        return {"website_quality":"POSSIBLE_REDESIGN" if issues else "HEALTHY", "website_audit_evidence":"; ".join(issues) if issues else "Homepage responded successfully with HTTPS, viewport, and contact evidence."}
    except Exception as exc:
        return {"website_quality":"WEBSITE_STATUS_UNCERTAIN", "website_audit_evidence":f"Audit could not establish website status: {exc}"}
