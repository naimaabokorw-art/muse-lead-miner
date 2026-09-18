# Muse Web Studio Lead Miner

This project is a Python lead-generation system designed to find local business prospects with evidence-based quality checks.

## What it does

- Discovers businesses from public search results.
- Cleans and deduplicates records.
- Verifies business identity and location.
- Finds likely website status.
- Collects public business emails and social profiles when available.
- Detects new or recently opened businesses.
- Audits websites for basic technical and conversion issues.
- Classifies leads and scores them transparently.
- Exports Excel and CSV files.

## Installation

From PowerShell:

```powershell
cd path\to\muse-lead-miner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Basic run:

```powershell
python run_muse.py --country Australia --city Sydney --niche "beauty salon" --limit 20
```

No-website mode:

```powershell
python run_muse.py --country Australia --city Sydney --niche "beauty salon" --limit 50 --mode no_website
```

New-business mode:

```powershell
python run_muse.py --country Australia --city Sydney --niche "beauty salon" --limit 50 --mode new_business
```

Redesign mode:

```powershell
python run_muse.py --country Australia --city Sydney --niche "beauty salon" --limit 50 --mode redesign
```

All mode (default):

```powershell
python run_muse.py --country Australia --city Sydney --niche "beauty salon" --limit 50 --mode all
```

Campaign queue:

```powershell
python run_muse.py --campaign campaigns.json
```

Resume:

```powershell
python run_muse.py --resume
```

## Configuration

The project reads settings from the CLI and `muse_lead_miner/config.py`.

You can also add more countries and niche phrases in the configuration module.

## Output files

Each campaign creates a folder under `data/runs/` with the pattern:

```text
data/runs/2026-09-18_2200_Australia_Sydney_beauty_salon/
```

This contains intermediate data and final export files including:

- `final_leads.xlsx`
- `final_leads.csv`
- `no_website_leads.xlsx`
- `new_business_leads.xlsx`
- `redesign_leads.xlsx`
- `rejected_leads.csv`
- `uncertain_leads.xlsx`
- `run_report.txt`

## Troubleshooting

- If a source blocks automation, the system records no data and moves on.
- If a website fails to load, the audit marks `BROKEN` or `UNCERTAIN` rather than crashing.
- Empty or uncertain values are kept as empty strings or explicit statuses rather than invented.

## Adding countries and niches

Edit `muse_lead_miner/config.py` to add countries or terms to `SUPPORTED_COUNTRIES` and `NICHE_DATABASE`.

## Understanding scores and uncertainty

- Scores are transparent and 0-100.
- Missing evidence lowers confidence.
- Uncertainty is represented with statuses like `UNCERTAIN`, `UNKNOWN`, and `NOT_FOUND` rather than guessed values.

## Notes

This is intentionally conservative. Quality matters more than raw volume.
