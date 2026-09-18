import os
from pathlib import Path


def ensure_exists(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


for directory in ["data", "data/runs", "logs", "tests"]:
    ensure_exists(directory)
