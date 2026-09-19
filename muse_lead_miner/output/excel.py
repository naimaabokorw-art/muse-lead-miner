from pathlib import Path
from typing import Any, Dict, Iterable, List
from openpyxl import Workbook

from muse_lead_miner.output.serialization import serialize_output_value


def write_xlsx(path: str | Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook(); ws = wb.active; ws.title = "Leads"; ws.append(fieldnames)
    for row in rows:
        ws.append([serialize_output_value(row.get(field, "")) for field in fieldnames])
    wb.save(path)
