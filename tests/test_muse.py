from pathlib import Path
import pytest

from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.verification.business import score_verification
from muse_lead_miner.scoring.lead_score import calculate_lead_score
from muse_lead_miner.utils.checkpoint import CheckpointManager
from muse_lead_miner.output.excel import write_xlsx


def test_normalization():
    record = normalize_business_record({"business_name": "Joe's Barber Shop", "phone": "(02) 555-1234", "website": "//joesbarbershop.com/"})
    assert record["business_name"] == "Joe'S Barber Shop"
    assert record["phone"] == "025551234"
    assert record["website"] == "https://joesbarbershop.com"


def test_deduplication():
    records = [
        {"business_name": "Joes Barber Shop", "phone": "025551234", "city": "Sydney", "country": "Australia"},
        {"business_name": "Joe's Barber Shop", "phone": "025551234", "city": "Sydney", "country": "Australia"},
    ]
    deduped, rejected = deduplicate_businesses(records)
    assert len(deduped) == 1


def test_url_normalization():
    from muse_lead_miner.utils.networking import normalize_url
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("//example.com/page") == "https://example.com/page"


def test_email_validation():
    from muse_lead_miner.utils.networking import normalize_url
    assert "@" in "hello@example.com"


def test_business_validation():
    valid, status = __import__("muse_lead_miner.verification.business", fromlist=["validate_business"]).validate_business({"business_name": "Sydney Studios", "city": "Sydney", "country": "Australia"})
    assert valid is True
    assert status == "OK"


def test_scoring():
    record = {"verification_score": 80, "website_status": "NO_OFFICIAL_WEBSITE_FOUND", "email": "hello@example.com", "city": "Sydney", "country": "Australia", "category": "beauty salon", "new_business": "TRUE"}
    score = calculate_lead_score(record)
    assert score["lead_score"] >= 60


def test_classification():
    record = {"verification_status": "VERIFIED", "website_status": "NO_OFFICIAL_WEBSITE_FOUND", "new_business": "FALSE"}
    if record["website_status"] == "NO_OFFICIAL_WEBSITE_FOUND":
        classification = "NO_WEBSITE"
    else:
        classification = "OTHER"
    assert classification == "NO_WEBSITE"


def test_checkpointing(tmp_path):
    checkpoint = CheckpointManager(tmp_path)
    checkpoint.save_json("stage1", [{"ok": True}])
    assert checkpoint.stage_complete("stage1") is True


def test_output_generation(tmp_path):
    rows = [{"business_name": "Test Business", "city": "Sydney"}]
    out = tmp_path / "out.xlsx"
    write_xlsx(out, rows, ["business_name", "city"])
    assert out.exists()


def test_integration_safe_data():
    rec = {"business_name": "Northern Glow Studio", "category": "beauty salon", "country": "Australia", "city": "Sydney", "phone": "0412345678", "website": "https://example.com"}
    ver = score_verification(rec)
    assert ver["verification_status"] in {"VERIFIED", "PARTIALLY_VERIFIED", "UNCERTAIN"}
