# Muse Web Studio Lead Miner

This branch is a free, evidence-first lead finder. It does **not** require an API key and does not claim that public web-search results are Google Maps data.

## Discovery source

The default source is `PUBLIC_WEB_SEARCH`, using conservative public HTML search results. OpenStreetMap is retained only as an optional supplemental provider. Google Places is not required and is not used by the default pipeline.

Results are explicitly labelled by source. Search engines may block automated requests or return incomplete data; the program retries briefly, logs the failure, and continues without bypassing protections.

## Install

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Free run

```bash
python main.py --country "United Arab Emirates" --city "Dubai" --niche "beauty salon" --limit 20 --mode all
```

## Modes

```bash
python main.py --country "United Arab Emirates" --city "Dubai" --niche "beauty salon" --limit 20 --mode no_website
python main.py --country "United Arab Emirates" --city "Dubai" --niche "beauty salon" --limit 20 --mode new_business
python main.py --input leads.csv --mode email_enrichment
```

For businesses without a known website, the pipeline searches public results for an official domain, rejects social/directory domains, retains the source URL and identity evidence, then extracts only publicly displayed emails from the official website. `NO_WEBSITE_FOUND_AFTER_SEARCH` means no strong official-domain match was found; it is not a mathematical proof that no site exists.

Outputs are written to `data/runs/YYYY-MM-DD/`.
