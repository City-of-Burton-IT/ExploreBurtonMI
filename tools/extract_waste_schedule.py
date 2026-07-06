# Build public/waste-schedule.json from the City's "Waste Schedule.xlsx" (street ->
# trash/recycling pickup day). Powers the collection-day lookup in the Resident
# Guide's Trash & Recycling section.
#
# The spreadsheet is a print-formatted sheet: the street is in column A and the day
# lands in whichever of columns B-J the formatting put it (usually F or G). A few
# long road descriptions wrap onto a second row that starts lowercase ("of ...").
# This parser reads the day from any column, falls back to a trailing day in the
# street cell, and merges lowercase continuation rows.
#
# Stdlib only (zipfile + ElementTree), no openpyxl dependency. The xlsx lives in
# docs/ (gitignored); the committed JSON is what the site reads.
#
# Re-runnable:  python tools/extract_waste_schedule.py
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from lib.iox import write_geojson
from lib.paths import REPO_ROOT, public_path

XLSX = os.path.join(REPO_ROOT, "docs", "Waste Schedule.xlsx")
OUT = public_path("waste-schedule.json")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

DAYS = {d.lower(): d for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")}
TRAILING_DAY = re.compile(r"(.*?)[\s]+(Monday|Tuesday|Wednesday|Thursday|Friday)\s*$", re.I)


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _load_grid(path: str) -> dict[int, dict[str, str]]:
    z = zipfile.ZipFile(path)
    shared = [
        "".join(t.text or "" for t in si.iter(NS + "t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml"))
    ]
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows: dict[int, dict[str, str]] = {}
    for c in sheet.iter(NS + "c"):
        v = c.find(NS + "v")
        if v is None:
            continue
        val = shared[int(v.text)] if c.get("t") == "s" else v.text
        m = re.match(r"([A-Z]+)(\d+)", c.get("r"))
        rows.setdefault(int(m.group(2)), {})[m.group(1)] = val
    return rows


def _day_in_row(row: dict[str, str]) -> str | None:
    for col in "BCDEFGHIJ":
        cv = _norm(row.get(col)).lower()
        if cv in DAYS:
            return DAYS[cv]
    return None


def parse(path: str) -> list[dict]:
    rows = _load_grid(path)
    entries: list[dict] = []
    pending: str | None = None  # a dayless street awaiting a continuation row
    for rn in sorted(rows):
        a = _norm(rows[rn].get("A"))
        if not a or a == "STREET" or "CITY OF BURTON" in a:
            continue
        day = _day_in_row(rows[rn])
        # Lowercase-leading row continues the previous (wrapped) street.
        if pending and a[:1].islower():
            a = f"{pending} {a}"
            pending = None
        if not day:
            m = TRAILING_DAY.match(a)
            if m:
                a, day = _norm(m.group(1)), DAYS[m.group(2).lower()]
        if day:
            entries.append({"street": a, "day": day})
        else:
            pending = a
    if pending:
        print(f"  WARNING: dangling street with no day: {pending!r}")
    # Stable sort by street name (case-insensitive).
    entries.sort(key=lambda e: e["street"].lower())
    return entries


def main() -> int:
    if not os.path.exists(XLSX):
        raise SystemExit(f"Spreadsheet not found: {XLSX}")
    entries = parse(XLSX)
    if not entries:
        raise SystemExit("No street/day rows parsed, check the sheet layout.")
    from collections import Counter
    by_day = dict(Counter(e["day"] for e in entries))
    payload = {
        "_source": "City of Burton Waste Removal Schedule (hauler: Emterra). Street -> pickup day.",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "entries": entries,
    }
    # Compact single-line style (same as the committed overlays).
    write_geojson(OUT, payload)
    print(f"Wrote {OUT}")
    print(f"  {len(entries)} streets; by day: {by_day}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
