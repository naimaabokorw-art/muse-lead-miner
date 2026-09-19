from pathlib import Path

def write_run_report(path, report):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Muse Lead Miner Run Report\n=========================\n" + "\n".join(f"{k}: {v}" for k, v in report.items()), encoding="utf-8")
