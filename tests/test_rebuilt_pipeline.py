from muse_lead_miner.cleaning.deduplicate import deduplicate_businesses
from muse_lead_miner.cleaning.normalize import normalize_business_record
from muse_lead_miner.detection.new_business import detect_new_business
from muse_lead_miner.enrichment.email import extract_emails
from muse_lead_miner.scrapers.discovery import PublicWebSearchProvider
from muse_lead_miner.verification.business import identity_match
from muse_lead_miner.verification.website import classify_website, discover_website

class Response:
    status_code = 200
    def __init__(self, text): self.text = text
    def raise_for_status(self): pass

def test_normalization_and_phone():
    r = normalize_business_record({"business_name": " Glow   Studio ", "phone": "+971 (50) 123-4567"})
    assert r["business_name"] == "Glow Studio" and r["phone"] == "971501234567"

def test_dedupe_place_id_and_merge():
    rows, rejected = deduplicate_businesses([{"business_name":"Glow", "google_place_id":"x", "source":"a"}, {"business_name":"Glow", "google_place_id":"x", "phone":"123", "source":"b"}])
    assert len(rows) == 1 and len(rejected) == 1 and rows[0]["phone"] == "123"

def test_public_search_parser_mocked():
    provider = PublicWebSearchProvider(session=type("S", (), {"headers": {}, "get": lambda *_a, **_k: Response('<div class="result"><h2 class="result__title"><a href="https://glow.example">Glow Beauty Studio</a></h2><a class="result__snippet">Beauty salon in Dubai</a></div>')})())
    assert provider.search("Glow Beauty Dubai")[0]["url"] == "https://glow.example"

def test_website_search_accepts_strong_match_and_rejects_directory():
    class Search:
        def search(self, query, limit=8, logger=None):
            return [{"title":"Glow Beauty Studio official website", "url":"https://glowbeauty.example", "snippet":"Glow Beauty Studio Dubai"}, {"title":"Glow Beauty Studio Yelp", "url":"https://yelp.com/biz/glow", "snippet":""}]
    result = discover_website({"business_name":"Glow Beauty Studio", "city":"Dubai"}, search=Search())
    assert result["website_status"] == "WEBSITE_FOUND"
    assert "yelp" not in result["website"]

def test_no_website_classification_after_search():
    class Search:
        def search(self, query, limit=8, logger=None): return []
    result = discover_website({"business_name":"Unknown Salon", "city":"Dubai"}, search=Search())
    assert result["website_status"] == "NO_WEBSITE_FOUND_AFTER_SEARCH"

def test_email_and_new_business():
    assert extract_emails("Call hello@example.com") == ["hello@example.com"]
    result = detect_new_business({"snippet":"newly opened in Dubai"})
    assert result["new_business"] == "TRUE"
    assert detect_new_business({})["new_business"] == "UNCERTAIN"

def test_false_identity():
    assert identity_match({"business_name":"Glow Beauty", "city":"Dubai"}, {"title":"Other Cafe", "snippet":"Dubai"})["identity_match_score"] < 75
