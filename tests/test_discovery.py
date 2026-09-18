from muse_lead_miner.scrapers.sources import build_discovery_queries, parse_duckduckgo_response


class FakeResponse:
    status_code = 200
    def __init__(self, text):
        self.text = text


def test_query_construction_is_dynamic():
    queries = build_discovery_queries("Australia", "New South Wales", "Sydney", "beauty salon")
    assert "beauty salon Sydney New South Wales Australia" in queries
    assert all("Sydney" in query for query in queries)


def test_duckduckgo_parser_accepts_candidates_without_website_or_email():
    html = '''<div class="result"><h2 class="result__title"><a href="https://directory.example/biz">Glow Studio</a></h2><a href="https://directory.example/biz">link</a><a class="result__snippet">Beauty salon in Sydney</a></div>'''
    rows, rejected = parse_duckduckgo_response(FakeResponse(html), "Australia", "", "Sydney", "beauty salon")
    assert rejected == 0
    assert len(rows) == 1
    assert rows[0]["business_name"] == "Glow Studio"
    assert rows[0]["website"] == ""
    assert rows[0]["source_url"] == "https://directory.example/biz"


def test_duckduckgo_parser_rejects_malformed_result():
    rows, rejected = parse_duckduckgo_response(FakeResponse('<div class="result"><span>no link</span></div>'), "Australia", "", "Sydney", "beauty salon")
    assert rows == []
    assert rejected == 1
