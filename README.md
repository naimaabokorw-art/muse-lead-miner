# Muse Web Studio Lead Miner

This rebuild uses Google Places API as the primary discovery source. It does not scrape Google Maps HTML and it never substitutes generic search results when Maps is unavailable.

## Install

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `GOOGLE_MAPS_API_KEY` for discovery. Input CSV/XLSX enrichment does not require a Maps key.

## Commands

```bash
python main.py --country "United Arab Emirates" --city Dubai --niche "beauty salon" --limit 100 --mode no_website
python main.py --country "United Arab Emirates" --city Dubai --niche "beauty salon" --limit 100 --mode new_business
python main.py --country "United Arab Emirates" --city Dubai --niche "beauty salon" --limit 100 --mode all
python main.py --input leads.csv --mode email_enrichment
```

Outputs are written to `data/runs/YYYY-MM-DD/`. Missing evidence stays blank or `UNCERTAIN`; public emails are not claimed deliverable.
