"""Turn the "Explore Burton City Property for Sale" SharePoint list into the
committed pipeline/data/city-property-sales.csv (ADR-0003 Part A self-service).

The Purchasing Department edits the list; a Power Automate flow sends EVERY row
to GitHub as a repository_dispatch (event "apply-city-property", payload
{"rows": [...]}); .github/workflows/apply-city-property.yml runs this tool, then
tools/build_city_property.py, and opens a review pull request. Full-set
regeneration: the list is the source of truth and the CSV is rewritten whole.

VALIDATION GATE: the rows are written to the CSV and then re-read with
build_city_property.read_rows(), the same checks the builder applies (track and
status enums, https packet links, ISO dates, numeric prices, one row per parcel).
Any failure exits non-zero so a bad list never reaches the public site.

Column mapping (SharePoint internal names on the left; see
planning/city-property-self-service.md for the list definition):

    Parcel, Address, Track, Status, Price, LotSize, Zoning, Listed, SoldDate,
    SoldPrice, Photo, Note, PacketUrl  ->  the CSV columns of the same meaning

Usage:
    python tools/sync_city_property.py --payload-file payload.json [--out path] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_city_property as bcp  # noqa: E402

OUT_CSV = bcp.SOURCE_CSV
CSV_COLUMNS = ["parcel", "address", "track", "status", "packet_url", "price", "lot_size",
               "zoning", "listed", "sold_date", "sold_price", "photo", "note"]
# SharePoint column -> CSV column. Several spellings are accepted so a renamed
# display column or a Title-based list still maps.
FIELD_MAP = {
    "parcel": ["Parcel", "ParcelNumber", "Title"],
    "address": ["Address", "SitusAddress"],
    "track": ["Track", "SaleTrack"],
    "status": ["Status"],
    "packet_url": ["PacketUrl", "PacketURL", "Packet"],
    "price": ["Price", "AskingPrice"],
    "lot_size": ["LotSize"],
    "zoning": ["Zoning"],
    "listed": ["Listed", "ListedDate"],
    "sold_date": ["SoldDate"],
    "sold_price": ["SoldPrice"],
    "photo": ["Photo"],
    "note": ["Note", "Notes"],
}
TRACK_ALIASES = {"no bid": "offer", "offer": "offer", "bid": "bid", "sealed bid": "bid", "bid required": "bid"}
STATUS_ALIASES = {"available": "available", "pending": "pending", "sale pending": "pending", "sold": "sold"}


def _get(row: dict, names: list[str]) -> str:
    for n in names:
        if n in row and row[n] not in (None, ""):
            v = row[n]
            # SharePoint sends choice/lookup/hyperlink fields as objects sometimes.
            if isinstance(v, dict):
                v = v.get("Value") or v.get("Url") or v.get("Description") or ""
            return str(v).strip()
    return ""


def _date(v: str) -> str:
    """SharePoint sends ISO datetimes ("2026-09-01T00:00:00Z"); keep the date part."""
    return v[:10] if v else ""


def rows_from_payload(payload: dict) -> list[dict]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("payload has no 'rows' list")
    out = []
    for r in rows:
        if not isinstance(r, dict):
            raise SystemExit("payload row is not an object")
        rec = {c: _get(r, names) for c, names in FIELD_MAP.items()}
        if not rec["parcel"] and not rec["address"]:
            continue  # blank list item
        rec["track"] = TRACK_ALIASES.get(rec["track"].lower(), rec["track"].lower())
        rec["status"] = STATUS_ALIASES.get(rec["status"].lower(), rec["status"].lower())
        rec["listed"] = _date(rec["listed"])
        rec["sold_date"] = _date(rec["sold_date"])
        out.append(rec)
    return out


def write_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["status"], r["address"])):
            w.writerow({c: r.get(c, "") for c in CSV_COLUMNS})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-file", required=True)
    ap.add_argument("--out", default=OUT_CSV)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(args.payload_file, encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = rows_from_payload(payload)
    print(f"Payload carries {len(rows)} listing rows")
    target = args.out if not args.dry_run else args.out + ".dryrun"
    write_csv(rows, target)
    # Validation gate: the builder's own reader must accept the file.
    validated = bcp.read_rows(target)
    print(f"Validated {len(validated)} rows -> {target}")
    if args.dry_run:
        os.remove(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
