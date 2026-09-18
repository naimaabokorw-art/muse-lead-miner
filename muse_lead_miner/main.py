from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from muse_lead_miner.config import MuseConfig, VALID_MODES
from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.scrapers.sources import discovery_source
from muse_lead_miner.verification.business import score_verification, validate_business
from muse_lead_miner.verification.website import discover_website
from muse_lead_miner.enrichment.email import enrich_email
from muse_lead_miner.enrichment.social import enrich_social
from muse_lead_miner.detection.new_business import detect_new_business
from muse_lead_miner.auditing.website_audit import audit_website
from muse_lead_miner.scoring.lead_score import calculate_lead_score
from muse_lead_miner.output.csv import write_csv
from muse_lead_miner.output.excel import write_xlsx
from muse_lead_miner.output.reports import write_run_report
from muse_lead_miner.utils.checkpoint import CheckpointManager
from muse_lead_miner.utils.logging import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Muse Web Studio lead miner")
    parser.add_argument("--country", default="Australia")
    parser.add_argument("--state", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--city", default="Sydney")
    parser.add_argument("--niche", default="beauty salon")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--mode", default="all", choices=sorted(VALID_MODES))
    parser.add_argument("--output-directory", default="data/runs")
    parser.add_argument("--min-lead-score", type=int, default=40)
    parser.add_argument("--request-timeout", type=int, default=15)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--request-delay", type=float, default=0.8)
    parser.add_argument("--max-concurrent-requests", type=int, default=4)
    parser.add_argument("--campaign", default="")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def build_run_directory(root: Path, config: MuseConfig) -> Path:
    run_dir = Path(config.output_directory) / config.run_folder_name
    run_dir.mkdir(parents=True, exist_ok=True)
    for sub in [
        "01_raw",
        "02_cleaned",
        "03_verified",
        "04_websites",
        "05_emails",
        "06_social",
        "07_new_business",
        "08_audited",
        "09_scored",
        "10_final",
    ]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    return run_dir


def run_campaign(config: MuseConfig) -> Dict[str, Any]:
    root = Path(".")
    run_dir = build_run_directory(root, config)
    logger = setup_logger(root / "logs" / "muse.log")
    checkpoint = CheckpointManager(run_dir)
    logger.info("[1/14] Business discovery")
    raw = discovery_source(config.country, config.region, config.city, config.niche, limit=config.limit)
    cleaned_records = [normalize_business_record(item) for item in raw[: config.limit]]
    checkpoint.save_json("01_raw", cleaned_records)

    logger.info("[2/14] Cleaning")
    deduped, rejected = deduplicate_businesses(cleaned_records)
    checkpoint.save_json("02_cleaned", deduped)

    logger.info("[3/14] Verification")
    verified = []
    for item in deduped:
        ok, reason = validate_business(item)
        if not ok:
            item["verification_status"] = "REJECTED"
            item["verification_score"] = 0
            item["verification_evidence"] = reason
            continue
        verification = score_verification(item)
        item.update(verification)
        verified.append(item)
    checkpoint.save_json("03_verified", verified)

    logger.info("[4/14] Website discovery")
    website_records = []
    for item in verified:
        item.update(discover_website(item))
        website_records.append(item)
    checkpoint.save_json("04_websites", website_records)

    logger.info("[5/14] Email enrichment")
    for item in website_records:
        item.update(enrich_email(item))
    checkpoint.save_json("05_emails", website_records)

    logger.info("[6/14] Social enrichment")
    social_records = []
    for item in website_records:
        item.update(enrich_social(item))
        social_records.append(item)
    checkpoint.save_json("06_social", social_records)

    logger.info("[7/14] New-business detection")
    new_records = []
    for item in social_records:
        item.update(detect_new_business(item, extra_text=f"{item.get('website_evidence', '')} {item.get('source_url', '')}"))
        new_records.append(item)
    checkpoint.save_json("07_new_business", new_records)

    logger.info("[8/14] Website auditing")
    audited = []
    for item in new_records:
        item.update(audit_website(item))
        audited.append(item)
    checkpoint.save_json("08_audited", audited)

    logger.info("[9/14] Classification")
    classified = []
    for item in audited:
        if item.get("verification_status") == "REJECTED":
            continue
        if item.get("website_status") == "NO_OFFICIAL_WEBSITE_FOUND":
            item["lead_category"] = "NO_WEBSITE"
        elif item.get("new_business") == "TRUE":
            item["lead_category"] = "NEW_BUSINESS"
        elif item.get("website_quality") == "POSSIBLE_REDESIGN":
            item["lead_category"] = "POSSIBLE_REDESIGN"
        elif item.get("website_status") == "WEBSITE_UNCERTAIN":
            item["lead_category"] = "WEBSITE_STATUS_UNCERTAIN"
        else:
            item["lead_category"] = "NOT_A_TARGET"
        item["personalization_notes"] = "Public business listing identified with available website, social, and contact evidence."
        classified.append(item)
    checkpoint.save_json("09_scored", classified)

    logger.info("[10/14] Scoring")
    scored = []
    for item in classified:
        score_info = calculate_lead_score(item)
        item.update(score_info)
        item["outreach_ready"] = "YES" if item.get("lead_score", 0) >= config.min_lead_score else "NO"
        item["outreach_reason"] = "Verified local business with enough evidence to justify outreach." if item["outreach_ready"] == "YES" else "Low confidence or insufficient evidence."
        item["date_found"] = datetime.now().strftime("%Y-%m-%d")
        scored.append(item)
    checkpoint.save_json("09_scored", scored)

    logger.info("[11/14] Quality control")
    final = [item for item in scored if item.get("lead_category") != "NOT_A_TARGET"]

    logger.info("[12/14] Export")
    fieldnames = [
        "business_name", "category", "country", "region", "city", "address", "phone",
        "email", "email_source", "email_type", "email_confidence", "website", "website_status",
        "website_quality", "website_evidence", "new_business", "new_business_confidence",
        "new_business_evidence", "instagram", "facebook", "tiktok", "linkedin", "source",
        "source_url", "verification_status", "verification_score", "lead_category", "lead_score",
        "score_breakdown", "outreach_ready", "outreach_reason", "personalization_notes", "date_found"
    ]
    write_csv(run_dir / "10_final" / "final_leads.csv", final, fieldnames)
    write_xlsx(run_dir / "10_final" / "final_leads.xlsx", final, fieldnames)
    write_xlsx(run_dir / "10_final" / "no_website_leads.xlsx", [r for r in final if r.get("lead_category") == "NO_WEBSITE"], fieldnames)
    write_xlsx(run_dir / "10_final" / "new_business_leads.xlsx", [r for r in final if r.get("lead_category") == "NEW_BUSINESS"], fieldnames)
    write_xlsx(run_dir / "10_final" / "redesign_leads.xlsx", [r for r in final if r.get("lead_category") == "POSSIBLE_REDESIGN"], fieldnames)
    write_xlsx(run_dir / "10_final" / "uncertain_leads.xlsx", [r for r in final if r.get("lead_category") == "WEBSITE_STATUS_UNCERTAIN"], fieldnames)
    rejected_rows = [{
        "business_name": item.get("business_name", ""),
        "reason_rejected": "DUPLICATE",
        "source": item.get("source", ""),
        "date_rejected": datetime.now().strftime("%Y-%m-%d"),
    } for item in rejected]
    write_csv(run_dir / "10_final" / "rejected_leads.csv", rejected_rows, ["business_name", "reason_rejected", "source", "date_rejected"])

    logger.info("[13/14] Report")
    report = {
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "country": config.country,
        "region": config.region,
        "city": config.city,
        "niche": config.niche,
        "requested_leads": config.limit,
        "discovered": len(raw),
        "cleaned": len(cleaned_records),
        "duplicates_removed": max(0, len(cleaned_records) - len(deduped)),
        "verified": len([r for r in verified if r.get("verification_status") in {"VERIFIED", "PARTIALLY_VERIFIED"}]),
        "website_found": len([r for r in final if r.get("website_status") in {"OFFICIAL_WEBSITE_FOUND", "SOCIAL_ONLY"}]),
        "no_website_found": len([r for r in final if r.get("website_status") == "NO_OFFICIAL_WEBSITE_FOUND"]),
        "website_uncertain": len([r for r in final if r.get("website_status") == "WEBSITE_UNCERTAIN"]),
        "new_businesses": len([r for r in final if r.get("new_business") == "TRUE"]),
        "redesign_opportunities": len([r for r in final if r.get("lead_category") == "POSSIBLE_REDESIGN"]),
        "public_emails_found": len([r for r in final if r.get("email")]),
        "no_public_email": len([r for r in final if not r.get("email")]),
        "rejected": len(rejected_rows),
        "final_leads": len(final),
        "outreach_ready": len([r for r in final if r.get("outreach_ready") == "YES"]),
        "source_failures": [],
    }
    write_run_report(run_dir / "run_report.txt", report)
    checkpoint.save_json("10_final", final)
    logger.info("Completed: %s", run_dir)
    return {"run_dir": str(run_dir), "final": final, "rejected": rejected_rows}


def main() -> None:
    args = parse_args()
    config = MuseConfig.from_args(args)
    run_campaign(config)


if __name__ == "__main__":
    main()
