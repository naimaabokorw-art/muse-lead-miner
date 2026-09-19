from pathlib import Path
import csv
from openpyxl import Workbook

def write_csv(path, rows, fields):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
        for row in rows: writer.writerow({field: row.get(field, "") for field in fields})

def write_xlsx(path, rows, fields):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook(); sheet = book.active; sheet.title = "Leads"; sheet.append(fields)
    for row in rows: sheet.append([row.get(field, "") for field in fields])
    book.save(path)
