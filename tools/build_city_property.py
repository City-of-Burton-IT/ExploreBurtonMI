"""Build the "City Property for Sale" overlay and dashboard (#177, ADR-0003 Part A).

The City of Burton sells tax-reverted and surplus parcels through the Purchasing
Department in two tracks: "No Bid" (Council-set asking price, offer form) and
"Bid Required" (sealed bid). Both are already public on burtonmi.gov. This tool
puts that inventory on the map and in a dashboard with links to the packets.

PUBLISHABLE BY CONSTRUCTION: every row is a parcel the City itself owns and has
already offered for sale, so no private owner, value or tax history appears. The
source CSV is therefore committed (unlike the Assessing exports). Former-owner
names, delinquency history and buyer names are NOT columns and must never be
added without a new ADR.

SOURCE: pipeline/data/city-property-sales.csv, maintained by Purchasing. Columns:

    parcel       BS&A parcel number, e.g. 59-12-776-262 (any punctuation)
    address      situs street line, e.g. 1234 E BRISTOL RD (blank number = vacant lot)
    track        offer | bid            (No Bid page vs Bid Required page)
    price        asking price in dollars (offer) or minimum bid (bid); blank = "Sealed bid"
    lot_size     free text, e.g. 60 x 120 ft or 0.41 acre
    zoning       zoning district code, e.g. R-1
    status       available | pending | sold
    listed       YYYY-MM-DD the parcel went on the list
    sold_date    YYYY-MM-DD when Council approved the sale (sold rows only)
    sold_price   dollars (sold rows only; the City is the seller, so this is public)
    photo        optional filename under public/property/ (City-owned photo)
    note         optional one-line public note
    packet_url   https link to the offer form or bid packet for this parcel

Coordinates come from the Census batch geocoder through build_address_points
(same cache), clipped to the city boundary. Sold rows older than SOLD_KEEP_DAYS
drop out so the public track record stays recent.

Re-runnable (committed outputs; the site reads the files, never the geocoder):
    pipeline/.venv/Scripts/python tools/build_city_property.py

Refresh recipe: Purchasing edits the CSV, run this script, commit
public/city-property.geojson and public/info-cityproperty.json.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date, datetime, timedelta

import build_address_points as bap
from lib.iox import write_geojson, write_json
from lib.paths import pipeline_data_path, public_path

SOURCE_CSV = pipeline_data_path("city-property-sales.csv")
OUT_GEOJSON = public_path("city-property.geojson")
OUT_INFO = public_path("info-cityproperty.json")

REQUIRED = ["parcel", "address", "track", "status", "packet_url"]
OPTIONAL = ["price", "lot_size", "zoning", "listed", "sold_date", "sold_price", "photo", "note"]
TRACKS = {"offer": "No bid: offer at asking price", "bid": "Sealed bid"}
STATUSES = {"available": "Available", "pending": "Sale pending", "sold": "Sold"}
COLORS = {"available": "#2e7d32", "pending": "#e65100", "sold": "#757575"}
SOLD_KEEP_DAYS = 365

OFFER_PAGE = "https://www.burtonmi.gov/departments/purchasing/city_property_sales_-_offer.php"
BID_PAGE = "https://burtonmi.gov/departments/purchasing/city_property_sales_-_bid_required.php"
PURCHASING_PAGE = "https://burtonmi.gov/departments/purchasing/"


def _norm(s) -> str:
    return " ".join(str(s or "").split()).strip()


def _money(value: str | None) -> int | None:
    """'12,500' / '$12500' / '' -> 12500 / 12500 / None. Anything else fails loud."""
    text = _norm(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return int(round(float(text)))
    except ValueError as exc:
        raise SystemExit(f"city-property: bad price value {value!r}") from exc


def _date(value: str | None, field: str, row_no: int) -> date | None:
    text = _norm(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(
            f"city-property: row {row_no} {field}={value!r} is not YYYY-MM-DD") from exc


def fmt_money(n: int | None) -> str:
    return f"${n:,}" if n is not None else "Sealed bid"


def read_rows(path: str = SOURCE_CSV) -> list[dict]:
    """Parse and validate the curated CSV. Zero data rows is allowed (the list can
    legitimately be empty) but a missing or renamed column stops the build."""
    if not os.path.exists(path):
        raise SystemExit(f"Source not found: {path}\nSee the module docstring for the schema.")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise SystemExit(f"city-property: source is missing columns {missing}")
        raw = list(reader)
    rows: list[dict] = []
    seen: set[str] = set()
    for i, r in enumerate(raw, start=2):  # line numbers as a human sees them
        parcel = _norm(r.get("parcel"))
        address = _norm(r.get("address"))
        if not parcel and not address:
            continue  # blank line
        track = _norm(r.get("track")).lower()
        status = _norm(r.get("status")).lower()
        if track not in TRACKS:
            raise SystemExit(f"city-property: row {i} track={track!r}; expected one of {sorted(TRACKS)}")
        if status not in STATUSES:
            raise SystemExit(f"city-property: row {i} status={status!r}; expected one of {sorted(STATUSES)}")
        if not address:
            raise SystemExit(f"city-property: row {i} ({parcel}) has no address")
        packet = _norm(r.get("packet_url"))
        if not packet.startswith("https://"):
            raise SystemExit(f"city-property: row {i} ({parcel}) packet_url must be https")
        if parcel in seen:
            raise SystemExit(f"city-property: parcel {parcel} appears twice")
        seen.add(parcel)
        sold_date = _date(r.get("sold_date"), "sold_date", i)
        if status == "sold" and sold_date is None:
            raise SystemExit(f"city-property: row {i} ({parcel}) is sold but has no sold_date")
        rows.append({
            "parcel": parcel,
            "address": address,
            "track": track,
            "price": _money(r.get("price")),
            "lot_size": _norm(r.get("lot_size")),
            "zoning": _norm(r.get("zoning")),
            "status": status,
            "listed": _date(r.get("listed"), "listed", i),
            "sold_date": sold_date,
            "sold_price": _money(r.get("sold_price")),
            "photo": _norm(r.get("photo")),
            "note": _norm(r.get("note")),
            "packet_url": packet,
            "lat": None,
            "lng": None,
        })
    return rows


def prune_old_sales(rows: list[dict], today: date, keep_days: int = SOLD_KEEP_DAYS) -> list[dict]:
    cutoff = today - timedelta(days=keep_days)
    return [r for r in rows if r["status"] != "sold" or r["sold_date"] >= cutoff]


def geocode(rows: list[dict]) -> None:
    """Fill lat/lng through the shared Census batch path and cache. Mutates rows."""
    for i, r in enumerate(rows):
        r.update({"id": str(i), "street": r["address"], "city": bap.DEFAULT_CITY,
                  "state": bap.DEFAULT_STATE, "zip": ""})
    cache = bap._load_cache()
    bap.geocode_batch(rows, cache)


def popup_rows(r: dict) -> list[list[str]]:
    rows = [
        ["Status", STATUSES[r["status"]]],
        ["How to buy", TRACKS[r["track"]]],
    ]
    if r["status"] == "sold":
        rows.append(["Sold", f"{fmt_money(r['sold_price'])} on {r['sold_date'].isoformat()}"])
    else:
        rows.append(["Asking price" if r["track"] == "offer" else "Minimum bid", fmt_money(r["price"])])
    if r["lot_size"]:
        rows.append(["Lot size", r["lot_size"]])
    if r["zoning"]:
        rows.append(["Zoning", r["zoning"]])
    rows.append(["Parcel", r["parcel"]])
    if r["note"]:
        rows.append(["Note", r["note"]])
    return rows


def build_geojson(rows: list[dict], rings: list[list]) -> tuple[dict, int, int]:
    """Point features for geocoded, in-city rows. Returns (fc, n_nocoord, n_outside)."""
    features = []
    nocoord = outside = 0
    for r in rows:
        if r["lat"] is None or r["lng"] is None:
            nocoord += 1
            continue
        if not bap.in_city(r["lng"], r["lat"], rings):
            outside += 1
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(r["lng"], 6), round(r["lat"], 6)]},
            "properties": {
                "name": bap.titlecase_street(r["address"]),
                "parcel": r["parcel"],
                "status": r["status"],
                "track": r["track"],
                "price": r["price"],
                "packet_url": r["packet_url"],
                "_color": COLORS[r["status"]],
                "_radius": 9 if r["status"] == "available" else 7,
                "_popupRows": popup_rows(r),
            },
        })
    return {"type": "FeatureCollection", "features": features}, nocoord, outside


def build_panel(rows: list[dict], today: date) -> dict:
    avail = [r for r in rows if r["status"] == "available"]
    pending = [r for r in rows if r["status"] == "pending"]
    sold = sorted((r for r in rows if r["status"] == "sold"), key=lambda r: r["sold_date"], reverse=True)
    offers = [r for r in avail if r["track"] == "offer" and r["price"] is not None]
    lowest = min((r["price"] for r in offers), default=None)

    stats = [
        {"label": "Parcels available now", "value": str(len(avail)),
         "hint": "City-owned, offered by the Purchasing Department"},
        {"label": "Fixed-price (no bid) parcels", "value": str(len([r for r in avail if r["track"] == "offer"])),
         "hint": "buy at the Council-set asking price"},
        {"label": "Sealed-bid parcels", "value": str(len([r for r in avail if r["track"] == "bid"])),
         "hint": "highest qualifying bid wins"},
        {"label": "Lowest asking price", "value": fmt_money(lowest) if lowest is not None else "None listed",
         "hint": "among fixed-price parcels"},
        {"label": "Sold in the last 12 months", "value": str(len(sold)),
         "hint": "Council-approved sales"},
    ]

    def listing_row(r: dict) -> dict:
        return {"cells": [
            bap.titlecase_street(r["address"]),
            "No bid" if r["track"] == "offer" else "Sealed bid",
            fmt_money(r["price"]),
            r["lot_size"] or "n/a",
            r["zoning"] or "n/a",
            STATUSES[r["status"]],
        ], "color": COLORS[r["status"]]}

    tables = [{
        "title": "City-owned property for sale",
        "columns": ["Address", "How to buy", "Price", "Lot size", "Zoning", "Status"],
        "rows": [listing_row(r) for r in sorted(avail + pending, key=lambda r: (r["status"], r["address"]))],
    }]
    if sold:
        tables.append({
            "title": "Sold in the last 12 months",
            "columns": ["Address", "Sold", "Sale price", "How it sold"],
            "rows": [{"cells": [
                bap.titlecase_street(r["address"]), r["sold_date"].isoformat(),
                fmt_money(r["sold_price"]), "No bid" if r["track"] == "offer" else "Sealed bid",
            ], "color": COLORS["sold"]} for r in sold],
        })

    links = [
        {"text": "City Property Sales: No Bid (offer at asking price)", "href": OFFER_PAGE},
        {"text": "City Property Sales: Bid Required", "href": BID_PAGE},
        {"text": "Purchasing Department", "href": PURCHASING_PAGE},
    ]
    # One link per distinct packet so a buyer can reach the form from the dashboard
    # (table cells are plain text by design).
    for url in sorted({r["packet_url"] for r in avail + pending} - {OFFER_PAGE, BID_PAGE, PURCHASING_PAGE}):
        links.append({"text": f"Offer or bid packet: {url.split('/')[-1] or url}", "href": url})

    notes = [
        "Turn on the \"City property for sale\" map overlay to see each parcel. Green pins are available, orange are sale pending, grey sold within the last year.",
        "Every sale needs City Council approval at a regular meeting, even at the asking price. Prices are set each year by Council resolution under Section 32.19 of the Codified Ordinances.",
        "A listing with no street number is usually a vacant lot. Contact Purchasing at (810) 743-1500 ext. 1801 with questions.",
    ]
    if not rows:
        notes.insert(0, "The Purchasing Department is confirming the current list. Until then, the two City Property Sales pages linked below are the authoritative inventory.")

    return {
        "title": "City Property for Sale",
        "subtitle": "Parcels the City of Burton is offering to buyers, with how to make an offer or bid",
        "lastUpdated": today.isoformat(),
        "stats": stats,
        "charts": [],
        "tables": tables,
        "source": "City of Burton Purchasing Department property-sale lists (No Bid and Bid Required), maintained by Purchasing.",
        "links": links,
        "notes": notes,
    }


def main() -> int:
    today = date.today()
    rows = prune_old_sales(read_rows(), today)
    print(f"Read {len(rows)} current rows from {os.path.basename(SOURCE_CSV)}")
    if not rows:
        print("  WARNING: no listings; writing an empty overlay and a placeholder panel")
    geocode(rows)
    rings = bap._rings_from_boundary()
    fc, nocoord, outside = build_geojson(rows, rings)
    write_geojson(OUT_GEOJSON, fc)
    write_json(OUT_INFO, build_panel(rows, today))
    print(f"Wrote {len(fc['features'])} parcels -> {os.path.basename(OUT_GEOJSON)} "
          f"(dropped {nocoord} un-geocoded, {outside} outside city)")
    print(f"Wrote {os.path.basename(OUT_INFO)}")
    if nocoord:
        print("  Un-geocoded rows stay in the dashboard table but not on the map; "
              "check the address spelling in the CSV.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
