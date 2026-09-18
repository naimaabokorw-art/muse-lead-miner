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

# Existing parse_args, build_run_directory, _safe_stage remain unchanged above.
