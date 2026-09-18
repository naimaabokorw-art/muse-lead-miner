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
    for name in ("01_raw", "02_cleaned", "03_verified", "04_websites", "05_emails", "06_social", "07_new_business", "08_audited", "09_scored", "10_final"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
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
    try:
        raw = discovery_source(config, logger=logger)
    except Exception as exc:
        logger.error("Discovery failed: %s", exc)
        raw, source_failures = [], [str(exc)]
    checkpoint.save_json("01_raw", raw)
    cleaned = [normalize_business_record(r) for r in raw[: max(0, config.limit)]]
    checkpoint.save_json("02_cleaned", cleaned)
    deduped, rejected = deduplicate_businesses(cleaned)
    verified = []
    for item in deduped:
        ok, reason = validate_business(item)
        if not ok:
            item.update(verification_status="REJECTED", verification_score=0, verification_evidence=reason)
            rejected.append({**item, "reason_rejected": reason})
            continue
        item.update(score_verification(item))
        verified.append(item)
    checkpoint.save_json("03_verified", verified)
    websites = _safe_stage(logger, "website discovery", verified, discover_website)
    checkpoint.save_json("04_websites", websites)
    emails = _safe_stage(logger, "email enrichment", websites, enrich_email)
    checkpoint.save_json("05_emails", emails)
    socials = _safe_stage(logger, "social enrichment", emails, enrich_social)
    checkpoint.save_json("06_social", socials)
    new_business = _safe_stage(logger, "new-business detection", socials, lambda r: detect_new_business(r, extra_text=r.get("snippet", "")))
    checkpoint.save_json("07_new_business", new_business)
    audited = _safe_stage(logger, "website audit", new_business, audit_website)
    checkpoint.save_json("08_audited", audited)

    classified = []
    for item in audited:
        if item.get("verification_status") == "REJECTED":
            continue
        website_status = item.get("website_status")
        if item.get("new_business") == "TRUE" and config.mode in {"all", "new_business"}:
            category = "NEW_BUSINESS"
        elif website_status == "NO_OFFICIAL_WEBSITE_FOUND" and config.mode in {"all", "no_website"}:
            category = "NO_WEBSITE"
        elif website_status == "WEBSITE_STATUS_UNCERTAIN":
            category = "WEBSITE_STATUS_UNCERTAIN"
        elif item.get("website_quality") == "POSSIBLE_REDESIGN" and config.mode in {"all", "redesign"}:
            category = "POSSIBLE_REDESIGN"
        else:
            category = "NOT_A_TARGET"
        item["lead_category"] = category
        observations = []
        if item.get("website"): observations.append(f"website observed: {item['website']}")
        if item.get("email"): observations.append(f"public email observed from {item.get('email_source_url', 'a public source')}")
        if item.get("website_audit_evidence"): observations.append(item["website_audit_evidence"])
        item["personalization_notes"] = "; ".join(observations) or "No additional public observations recorded."
        item.update(calculate_lead_score(item))
        item["outreach_ready"] = "YES" if item["lead_score"] >= config.min_lead_score and category not in {"WEBSITE_STATUS_UNCERTAIN", "NOT_A_TARGET"} else "NO"
        item["outreach_reason"] = "Deterministic score threshold met with recorded public evidence." if item["outreach_ready"] == "YES" else "Insufficient confidence or target evidence."
        item["date_found"] = started.strftime("%Y-%m-%d")
        classified.append(item)
    checkpoint.save_json("09_scored", classified)
    final = [r for r in classified if r.get("lead_category") != "NOT_A_TARGET"]
    fields = ["business_name","category","country","region","city","address","phone","email","email_source","email_type","email_confidence","email_status","website","website_status","website_quality","website_evidence","website_audit_evidence","new_business","new_business_confidence","new_business_evidence","instagram","facebook","tiktok","linkedin","source","source_url","verification_status","verification_score","verification_evidence","lead_category","lead_score","score_breakdown","outreach_ready","outreach_reason","personalization_notes","date_found"]
    out = run_dir / "10_final"
    write_csv(out / "final_leads.csv", final, fields)
    write_xlsx(out / "final_leads.xlsx", final, fields)
    for filename, category in (("no_website_leads.xlsx", "NO_WEBSITE"), ("new_business_leads.xlsx", "NEW_BUSINESS"), ("redesign_leads.xlsx", "POSSIBLE_REDESIGN"), ("uncertain_leads.xlsx", "WEBSITE_STATUS_UNCERTAIN")):
        write_xlsx(out / filename, [r for r in final if r.get("lead_category") == category], fields)
    rejected_rows = [{"business_name": r.get("business_name", ""), "reason_rejected": r.get("reason_rejected", "DUPLICATE"), "source": r.get("source", ""), "date_rejected": started.strftime("%Y-%m-%d")} for r in rejected]
    write_csv(out / "rejected_leads.csv", rejected_rows, ["business_name", "reason_rejected", "source", "date_rejected"])
    report = {"start_time": started.isoformat(timespec="seconds"), "end_time": datetime.now().isoformat(timespec="seconds"), "country": config.country, "region": config.region, "city": config.city, "niche": config.niche, "mode": config.mode, "requested_leads": config.limit, "discovered": len(raw), "cleaned": len(cleaned), "verified": len(verified), "final_leads": len(final), "rejected": len(rejected_rows), "source_failures": source_failures}
    write_run_report(out / "run_report.txt", report)
    checkpoint.save_json("10_final", final)
    return {"run_dir": str(run_dir), "final": final, "rejected": rejected_rows}


def _campaigns(path: str) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("campaigns", [data])


def main() -> None:
    args = parse_args()
    if args.campaign:
        for campaign in _campaigns(args.campaign):
            merged = vars(args).copy(); merged.update(campaign)
            run_campaign(MuseConfig.from_args(argparse.Namespace(**merged)))
    else:
        run_campaign(MuseConfig.from_args(args))


if __name__ == "__main__":
    main()
