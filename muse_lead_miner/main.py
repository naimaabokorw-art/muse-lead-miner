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
from muse_lead_miner.scrapers.discovery import discovery_source
from muse_lead_miner.verification.website import classify_website

def parse_input(path):
    if path.lower().endswith(".xlsx"):
        sheet = load_workbook(path, read_only=True, data_only=True).active
        rows = list(sheet.values); return [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []
    with open(path, newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def parser():
    p = argparse.ArgumentParser(description="Evidence-first Google Maps lead miner")
    p.add_argument("--country", default=""); p.add_argument("--city", default=""); p.add_argument("--region", default="")
    p.add_argument("--niche", default=""); p.add_argument("--limit", type=int, default=25)
    p.add_argument("--mode", choices=sorted(VALID_MODES), default="all"); p.add_argument("--input", default="")
    p.add_argument("--output-directory", default="data/runs"); p.add_argument("--verify-websites", action="store_true")
    p.add_argument("--timeout", type=int, default=15); p.add_argument("--retries", type=int, default=3); p.add_argument("--delay", type=float, default=.25)
    return p

def process(config):
    run = Path(config.output_directory) / date.today().isoformat(); run.mkdir(parents=True, exist_ok=True)
    raw = parse_input(config.input_path) if config.input_path else discovery_source(config)
    rows = [normalize_business_record(x) for x in raw[:config.limit] if x]
    rows, rejected = deduplicate_businesses(rows)
    for row in rows:
        row.update(classify_website(row)); row.update(enrich_email(row)); row.update(detect_new_business(row))
        row["date_found"] = date.today().isoformat(); row["lead_category"] = "NO_WEBSITE" if row["website_status"] == "NO_WEBSITE_CONFIRMED" else "NEW_BUSINESS" if row["new_business"] == "TRUE" else "WEBSITE_STATUS_UNCERTAIN"
    if config.mode == "no_website": final = [x for x in rows if x["website_status"] == "NO_WEBSITE_CONFIRMED"]
    elif config.mode == "new_business": final = [x for x in rows if x["new_business"] == "TRUE"]
    elif config.mode == "email_enrichment": final = rows
    else: final = [x for x in rows if x["lead_category"] in {"NO_WEBSITE", "NEW_BUSINESS", "WEBSITE_STATUS_UNCERTAIN"}]
    write_csv(run / "final_leads.csv", final, OUTPUT_FIELDS); write_xlsx(run / "final_leads.xlsx", final, OUTPUT_FIELDS)
    for name, selected in (("no_website_leads", [x for x in rows if x["lead_category"] == "NO_WEBSITE"]), ("new_business_leads", [x for x in rows if x["lead_category"] == "NEW_BUSINESS"]), ("email_enriched_leads", rows), ("uncertain_leads", [x for x in rows if x["website_status"] == "WEBSITE_STATUS_UNCERTAIN"])):
        write_csv(run / f"{name}.csv", selected, OUTPUT_FIELDS); write_xlsx(run / f"{name}.xlsx", selected, OUTPUT_FIELDS)
    write_run_report(run / "run_report.txt", {"mode": config.mode, "discovered": len(raw), "deduplicated": len(rows), "duplicates_or_rejected": len(rejected), "exported": len(final), "google_maps_api_required": not bool(config.input_path)})
    return {"run_dir": str(run), "final": final, "rejected": rejected}

def main():
    args = parser().parse_args(); process(MuseConfig.from_args(args))

if __name__ == "__main__": main()
