from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.detection.new_business import detect_new_business
from muse_lead_miner.enrichment.email import extract_emails
from muse_lead_miner.verification.business import identity_match
from muse_lead_miner.verification.website import classify_website

def test_normalization_and_phone():
    r = normalize_business_record({"business_name":" Glow   Studio ", "phone":"+971 (50) 123-4567"})
    assert r["business_name"] == "Glow Studio" and r["phone"] == "971501234567"

def test_dedupe_place_id_and_merge():
    rows, rejected = deduplicate_businesses([{"business_name":"Glow", "google_place_id":"x", "source":"a"}, {"business_name":"Glow", "google_place_id":"x", "phone":"123", "source":"b"}])
    assert len(rows) == 1 and len(rejected) == 1 and rows[0]["phone"] == "123"

def test_website_status_never_invents_no_website():
    assert classify_website({})["website_status"] == "WEBSITE_STATUS_UNCERTAIN"
    assert classify_website({"website_status":"NO_WEBSITE_CONFIRMED"})["website_status"] == "NO_WEBSITE_CONFIRMED"

def test_identity_rejects_false_match():
    result = identity_match({"business_name":"Glow Beauty", "city":"Dubai"}, {"business_name":"Other Cafe", "city":"Dubai", "website":"https://other.example"})
    assert result["identity_match_score"] < 70

def test_email_extraction_and_new_business():
    assert extract_emails("Call hello@example.com") == ["hello@example.com"]
    assert detect_new_business({"snippet":"newly opened in Dubai"})["new_business"] == "TRUE"
    assert detect_new_business({})["new_business"] == "UNCERTAIN"
