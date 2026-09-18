from pathlib import Path
from typing import Any, Dict

def write_run_report(path: str | Path, report: Dict[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for key, value in report.items(): fp.write(f"{key}: {value}\n")
