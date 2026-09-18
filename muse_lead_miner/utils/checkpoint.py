import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class CheckpointManager:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_json(self, stage: str, payload: Any):
        stage_dir = self.root / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        out_file = stage_dir / "data.json"
        with open(out_file, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

    def load_json(self, stage: str):
        file_path = self.root / stage / "data.json"
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as fp:
            try:
                return json.load(fp)
            except json.JSONDecodeError:
                return []

    def stage_complete(self, stage: str) -> bool:
        return (self.root / stage / "data.json").exists()

    def last_completed_stage(self, stages: Iterable[str]) -> str:
        completed = []
        for stage in stages:
            if self.stage_complete(stage):
                completed.append(stage)
        return completed[-1] if completed else ""
