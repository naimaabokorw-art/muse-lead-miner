from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses


def test_deduplicate_punctuation_whitespace_case_and_phone_formatting():
    records = [
        {"business_name": "  JOE'S   BARBER SHOP ", "phone": "+61 (02) 555-1234", "city": "SYDNEY", "country": "AUSTRALIA", "address": "1 Main St"},
        {"business_name": "Joes Barber Shop", "phone": "025551234", "city": "Sydney", "country": "Australia", "website": "https://joes.example"},
    ]
    deduped, rejected = deduplicate_businesses(records)
    assert len(deduped) == 1
    assert len(rejected) == 1
    assert deduped[0]["address"] == "1 Main St"
    assert deduped[0]["website"] == "https://joes.example"


def test_deduplicate_normalized_name_and_location_without_phone():
    records = [
        {"business_name": "North Glow Studio", "city": "Sydney", "country": "Australia"},
        {"business_name": "north-glow studio", "city": " Sydney ", "country": "australia", "category": "beauty salon"},
    ]
    deduped, _ = deduplicate_businesses(records)
    assert len(deduped) == 1
    assert deduped[0]["category"] == "beauty salon"


def test_deduplicate_does_not_merge_different_locations():
    records = [
        {"business_name": "Same Name Studio", "phone": "025551234", "city": "Sydney", "country": "Australia"},
        {"business_name": "Same Name Studio", "phone": "025551234", "city": "Melbourne", "country": "Australia"},
    ]
    deduped, _ = deduplicate_businesses(records)
    assert len(deduped) == 2
