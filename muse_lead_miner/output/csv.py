import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

def write_csv(path: str | Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore"); writer.writeheader()
        for row in rows: writer.writerow({k: row.get(k, "") for k in fieldnames})
