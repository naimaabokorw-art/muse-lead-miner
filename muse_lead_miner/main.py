from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from muse_lead_miner.auditing.website_audit import audit_website
from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.config import MuseConfig, VALID_MODES
from muse_lead_miner.detection.new_business import detect_new_business
from muse_lead_miner.enrichment.email import enrich_email
from muse_lead_miner.enrichment.social import enrich_social
from muse_lead_miner.output.csv import write_csv
from muse_lead_miner.output.excel import write_xlsx
from muse_lead_miner.output.reports import write_run_report
from muse_lead_miner.scoring.lead_score import calculate_lead_score
from muse_lead_miner.scrapers.sources import discovery_source
from muse_lead_miner.utils.checkpoint import CheckpointManager
from muse_lead_miner.utils.logging import setup_logger
from muse_lead_miner.verification.business import score_verification, validate_business
from muse_lead_miner.verification.website import discover_website


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
    run_dir = root / config.output_directory / config.run_folder_name
    stages = ("01_raw", "02_cleaned", "03_verified", "04_websites", "05_emails", "06_social", "07_new_business", "08_audited", "09_scored", "10_final")
    for stage in stages:
        (run_dir / stage).mkdir(parents=True, exist_ok=True)
    return run_dir


def _safe_stage(logger: logging.Logger, name: str, records: Iterable[Dict[str, Any]], function) -> List[Dict[str, Any]]:
    output = []
    for record in records:
        try:
            record.update(function(record) or {})
        except Exception as exc:
            logger.error("%s failed for %s: %s", name, record.get("business_name", "unknown"), exc)
            record.setdefault("pipeline_errors", []).append(f"{name}: {exc}")
        output.append(record)
    return output


def run_campaign(config: MuseConfig) -> Dict[str, Any]:
    root = Path.cwd()
    run_dir = build_run_directory(root, config)
    logger = setup_logger(root / "logs" / "muse.log")
    checkpoint = CheckpointManager(run_dir)
    started = datetime.now()
    source_failures: List[str] = []

    def stage(label: str) -> None:
        logger.info("[%s]", label)

    stage("DISCOVERY")
    try:
        raw = discovery_source(config, logger=logger)
    except Exception as exc:
        logger.exception("Discovery failed")
        raw, source_failures = [], [str(exc)]
    logger.info("Discovery returned %d public records", len(raw))
    checkpoint.save_json("01_raw", raw)

    stage("CLEANING")
    cleaned = [normalize_business_record(item) for item in raw[:max(0, config.limit)]]
    checkpoint.save_json("02_cleaned", cleaned)

    stage("DEDUPLICATION")
    deduped, rejected = deduplicate_businesses(cleaned)
    logger.info("Retained %d records; rejected %d duplicates or malformed records", len(deduped), len(rejected))

    stage("VERIFICATION")
    verified = []
    for item in deduped:
        valid, reason = validate_business(item)
        if not valid:
            rejected.append({**item, "reason_rejected": reason})
            continue
        item.update(score_verification(item))
        verified.append(item)
    checkpoint.save_json("03_verified", verified)

    stage("WEBSITE DISCOVERY")
    websites = _safe_stage(logger, "website discovery", verified, discover_website)
    checkpoint.save_json("04_websites", websites)

    stage("EMAIL ENRICHMENT")
    emails = _safe_stage(logger, "email enrichment", websites, enrich_email)
    checkpoint.save_json("05_emails", emails)

    stage("VALIDATION")
    logger.info("Email validation is limited to public-source and syntax checks; deliverability is not claimed")
    checkpoint.save_json("06_social", emails)

    stage("SOCIAL ENRICHMENT")
    socials = _safe_stage(logger, "social enrichment", emails, enrich_social)
    checkpoint.save_json("07_new_business", socials)

    stage("NEW BUSINESS DETECTION")
    enriched = _safe_stage(logger, "new-business detection", socials, lambda record: detect_new_business(record, extra_text=record.get("snippet", "")))

    stage("WEBSITE AUDIT")
    audited = _safe_stage(logger, "website audit", enriched, audit_website)
    checkpoint.save_json("08_audited", audited)

    stage("CLASSIFICATION")
    classified = []
    for item in audited:
        status = item.get("website_status")
        if item.get("new_business") == "TRUE" and config.mode in {"all", "new_business"}:
            category = "NEW_BUSINESS"
        elif status == "NO_OFFICIAL_WEBSITE_FOUND" and config.mode in {"all", "no_website"}:
            category = "NO_WEBSITE"
        elif status == "WEBSITE_STATUS_UNCERTAIN":
            category = "WEBSITE_STATUS_UNCERTAIN"
        elif item.get("website_quality") == "POSSIBLE_REDESIGN" and config.mode in {"all", "redesign"}:
            category = "POSSIBLE_REDESIGN"
        else:
            category = "NOT_A_TARGET"
        item["lead_category"] = category
        item["personalization_notes"] = item.get("website_audit_evidence") or "No additional public observations recorded."
        classified.append(item)

    stage("SCORING")
    for item in classified:
        item.update(calculate_lead_score(item))
        item["outreach_ready"] = "YES" if item["lead_score"] >= config.min_lead_score and item["lead_category"] not in {"NOT_A_TARGET", "WEBSITE_STATUS_UNCERTAIN"} else "NO"
        item["date_found"] = started.strftime("%Y-%m-%d")
    checkpoint.save_json("09_scored", classified)

    stage("EXPORT")
    final = [item for item in classified if item.get("lead_category") != "NOT_A_TARGET"]
    fields = ["business_name", "category", "country", "region", "city", "address", "phone", "email", "email_source", "email_type", "email_confidence", "email_status", "website", "website_status", "website_quality", "website_evidence", "website_audit_evidence", "new_business", "new_business_confidence", "new_business_evidence", "instagram", "facebook", "tiktok", "linkedin", "source", "source_url", "verification_status", "verification_score", "verification_evidence", "lead_category", "lead_score", "score_breakdown", "outreach_ready", "personalization_notes", "date_found"]
    output = run_dir / "10_final"
    write_csv(output / "final_leads.csv", final, fields)
    write_xlsx(output / "final_leads.xlsx", final, fields)
    for filename, category in (("no_website_leads.xlsx", "NO_WEBSITE"), ("new_business_leads.xlsx", "NEW_BUSINESS"), ("redesign_leads.xlsx", "POSSIBLE_REDESIGN"), ("uncertain_leads.xlsx", "WEBSITE_STATUS_UNCERTAIN")):
        write_xlsx(output / filename, [item for item in final if item.get("lead_category") == category], fields)
    rejected_rows = [{"business_name": item.get("business_name", ""), "reason_rejected": item.get("reason_rejected", "DUPLICATE"), "source": item.get("source", ""), "date_rejected": started.strftime("%Y-%m-%d")} for item in rejected]
    write_csv(output / "rejected_leads.csv", rejected_rows, ["business_name", "reason_rejected", "source", "date_rejected"])
    write_run_report(output / "run_report.txt", {"start_time": started.isoformat(timespec="seconds"), "end_time": datetime.now().isoformat(timespec="seconds"), "country": config.country, "region": config.region, "city": config.city, "niche": config.niche, "mode": config.mode, "requested_leads": config.limit, "discovered": len(raw), "final_leads": len(final), "rejected": len(rejected_rows), "source_failures": source_failures})
    checkpoint.save_json("10_final", final)
    logger.info("Completed run: %s (%d final leads)", run_dir, len(final))
    return {"run_dir": str(run_dir), "final": final, "rejected": rejected_rows}


def _campaigns(path: str) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("campaigns"), list):
        return data["campaigns"]
    if isinstance(data, dict):
        return [data]
    raise ValueError("Campaign file must contain an object or a list of objects")


def _latest_run(config: MuseConfig) -> Path | None:
    root = Path.cwd() / config.output_directory
    if not root.exists():
        return None
    prefix = f"{config.country.replace(' ', '_')}_{config.city.replace(' ', '_')}_{config.niche.replace(' ', '_')}"
    candidates = sorted((path for path in root.iterdir() if path.is_dir() and path.name.endswith(prefix)), reverse=True)
    return candidates[0] if candidates else None


def main() -> None:
    args = parse_args()
    if args.campaign:
        campaigns = _campaigns(args.campaign)
        if not campaigns:
            raise ValueError(f"No campaigns found in {args.campaign}")
        for campaign in campaigns:
            values = vars(args).copy()
            values.update(campaign)
            run_campaign(MuseConfig.from_args(argparse.Namespace(**values)))
        return

    config = MuseConfig.from_args(args)
    if config.resume:
        previous = _latest_run(config)
        if previous:
            print(f"[RESUME] Existing run found at {previous}; rerunning incomplete pipeline stages", flush=True)
        else:
            print("[RESUME] No previous matching run found; starting a new run", flush=True)
    run_campaign(config)


if __name__ == "__main__":
    main()
