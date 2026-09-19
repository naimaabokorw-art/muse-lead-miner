# Muse Web Studio Lead Miner

This version uses Google Places only when `GOOGLE_MAPS_API_KEY` is configured. If you do not want API keys, it automatically uses the free OpenStreetMap Nominatim provider. That fallback is clearly labeled as `openstreetmap_nominatim` and is not presented as Google Maps data.

## Install

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Free no-key run

```bash
python main.py --country "United Arab Emirates" --city Dubai --niche "beauty salon" --limit 10 --mode all
```

The free provider is rate-limited and may return less complete business data than Google Places. It does not reliably provide phone numbers, websites, ratings, or review counts, so missing fields remain blank or uncertain.

## CSV/XLSX enrichment without discovery

```bash
python main.py --input leads.csv --mode email_enrichment
```

Outputs are written to `data/runs/YYYY-MM-DD/`.
