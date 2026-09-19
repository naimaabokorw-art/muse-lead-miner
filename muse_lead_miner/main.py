from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from openpyxl import load_workbook

from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.config import MuseConfig, OUTPUT_FIELDS, VALID_MODES
from muse_lead_miner.detection.new_business import detect_new_business
from muse_lead_miner.enrichment.email import enrich_email
from muse_lead_miner.output.files import write_csv, write_xlsx
from muse_lead_miner.output.reports import write_run_report
from muse_lead_miner.scrapers.discovery import PublicWebSearchProvider, discovery_source
from muse_lead_miner.verification.website import classify_website, discover_website


def parse_input(path):
    if path.lower().endswith(".xlsx"):
        sheet = load_workbook(path, read_only=True, data_only=True).active
        rows = list(sheet.values)
        return [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def parser():
    p = argparse.ArgumentParser(description="Free evidence-first public web lead miner")
    p.add_argument("--country", default=""); p.add_argument("--city", default=""); p.add_argument("--region", default="")
    p.add_argument("--niche", default=""); p.add_argument("--limit", type=int, default=25)
    p.add_argument("--mode", choices=sorted(VALID_MODES), default="all"); p.add_argument("--input", default="")
    p.add_argument("--output-directory", default="data/runs"); p.add_argument("--verify-websites", action="store_true")
    p.add_argument("--timeout", type=int, default=15); p.add_argument("--retries", type=int, default=2); p.add_argument("--delay", type=float, default=1.0)
    return p


def process(config):
    run = Path(config.output_directory) / date.today().isoformat(); run.mkdir(parents=True, exist_ok=True)
    raw = parse_input(config.input_path) if config.input_path else discovery_source(config)
    rows, rejected = deduplicate_businesses([normalize_business_record(x) for x in raw[:config.limit] if x])
    search = PublicWebSearchProvider(timeout=config.timeout, retries=config.retries, delay=config.delay)
    for row in rows:
        try:
            row.update(discover_website(row, search=search))
        except Exception:
            row.update({"website_status": "WEBSITE_STATUS_UNCERTAIN", "website_source": "", "website_source_url": ""})
        row.update(enrich_email(row))
        row.update(detect_new_business(row, extra_text=row.get("search_snippet", "")))
        row["date_found"] = date.today().isoformat()
        row["lead_category"] = "NO_WEBSITE" if row.get("website_status") == "NO_WEBSITE_FOUND_AFTER_SEARCH" else "NEW_BUSINESS" if row.get("new_business") == "TRUE" else "WEBSITE_STATUS_UNCERTAIN"
    if config.mode == "no_website": final = [x for x in rows if x["lead_category"] == "NO_WEBSITE"]
    elif config.mode == "new_business": final = [x for x in rows if x["new_business"] == "TRUE"]
    elif config.mode == "email_enrichment": final = rows
    else: final = [x for x in rows if x["lead_category"] in {"NO_WEBSITE", "NEW_BUSINESS", "WEBSITE_STATUS_UNCERTAIN"}]
    write_csv(run / "final_leads.csv", final, OUTPUT_FIELDS); write_xlsx(run / "final_leads.xlsx", final, OUTPUT_FIELDS)
    groups = {"no_website_leads": [x for x in rows if x["lead_category"] == "NO_WEBSITE"], "new_business_leads": [x for x in rows if x["lead_category"] == "NEW_BUSINESS"], "email_enriched_leads": rows, "uncertain_leads": [x for x in rows if x["lead_category"] == "WEBSITE_STATUS_UNCERTAIN"]}
    for name, selected in groups.items():
        write_csv(run / f"{name}.csv", selected, OUTPUT_FIELDS); write_xlsx(run / f"{name}.xlsx", selected, OUTPUT_FIELDS)
    write_run_report(run / "run_report.txt", {"mode": config.mode, "discovery_source": "PUBLIC_WEB_SEARCH" if not config.input_path else "CSV_INPUT", "api_key_required": False, "discovered": len(raw), "deduplicated": len(rows), "duplicates_or_rejected": len(rejected), "exported": len(final)})
    return {"run_dir": str(run), "final": final, "rejected": rejected}


def main():
    args = parser().parse_args(); process(MuseConfig.from_args(args))

if __name__ == "__main__": main()
