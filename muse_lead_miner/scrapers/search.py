from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


def write_run_report(path: str | Path, payload: Dict[str, Any]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Muse Lead Miner Run Report",
        "=" * 30,
        f"Start time: {payload.get('start_time') or 'UNKNOWN'}",
        f"End time: {payload.get('end_time') or 'UNKNOWN'}",
        f"Country: {payload.get('country') or 'UNKNOWN'}",
        f"Region: {payload.get('region') or 'UNKNOWN'}",
        f"City: {payload.get('city') or 'UNKNOWN'}",
        f"Niche: {payload.get('niche') or 'UNKNOWN'}",
        f"Requested leads: {payload.get('requested_leads') or 0}",
        f"Discovered: {payload.get('discovered') or 0}",
        f"Cleaned: {payload.get('cleaned') or 0}",
        f"Duplicates removed: {payload.get('duplicates_removed') or 0}",
        f"Verified: {payload.get('verified') or 0}",
        f"Website found: {payload.get('website_found') or 0}",
        f"No website found: {payload.get('no_website_found') or 0}",
        f"Website uncertain: {payload.get('website_uncertain') or 0}",
        f"New businesses: {payload.get('new_businesses') or 0}",
        f"Redesign opportunities: {payload.get('redesign_opportunities') or 0}",
        f"Public emails found: {payload.get('public_emails_found') or 0}",
        f"No public email: {payload.get('no_public_email') or 0}",
        f"Rejected: {payload.get('rejected') or 0}",
        f"Final leads: {payload.get('final_leads') or 0}",
        f"Outreach-ready leads: {payload.get('outreach_ready') or 0}",
        "",
        "Source-level failures:",
    ]
    for failure in payload.get("source_failures", []):
        lines.append(f"- {failure}")
    path.write_text("\n".join(lines), encoding="utf-8")
