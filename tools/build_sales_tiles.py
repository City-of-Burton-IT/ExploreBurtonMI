"""Build the "Home Sale Prices" block-group tiles and dashboard (#178, ADR-0003 Part B).

What homes sell for, by neighbourhood, published ONLY as aggregates over Census
block groups. No parcel number, address, sale date or individual price leaves
this machine: the public files carry per-group counts, medians and changes, and
any group with fewer than MIN_SALES qualifying sales in the window shows no value.

SOURCE: pipeline/data/sales-source.csv from tools/Export-BsaSales.ps1 (gitignored).
Columns: parcel, street, city, zip, saledate, price, propclass, terms, instr,
sqft, vacant, liberpage. Arms-length coding (terms 03/19) and the confidential
flag are already applied by the export; this tool applies the rest of ADR-0003:

  * improved parcels only (vacant = 0) and a recorded price above zero;
  * a multi-parcel sale (same liber/page, date and price) counts once, and its
    price per square foot is not used because the price covers several parcels;
  * current window = trailing 24 months, prior window = the 24 months before it.

Geocoding goes through the shared Census batch path and cache used by
build_address_points.py, then each sale is assigned to the block group polygon
that contains it (public/block-groups.geojson from tools/fetch_block_groups.py).

Outputs: public/sales-tiles.geojson (overlay) and public/info-homesales.json (panel).

Re-runnable (committed outputs; the site reads the files, never the geocoder):
    pipeline/.venv/Scripts/python tools/build_sales_tiles.py
"""
from __future__ import annotations

import csv
import os
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

import build_address_points as bap
from fetch_block_groups import contains, rings_of
from lib.iox import write_geojson, write_json
from lib.paths import pipeline_data_path, public_path

SOURCE_CSV = pipeline_data_path("sales-source.csv")
BLOCK_GROUPS = public_path("block-groups.geojson")
OUT_GEOJSON = public_path("sales-tiles.geojson")
OUT_INFO = public_path("info-homesales.json")

REQUIRED = ["street", "saledate", "price", "propclass", "sqft", "vacant", "liberpage"]
MIN_SALES = 5          # ADR-0003 suppression floor
WINDOW_DAYS = 730      # trailing 24 months
# Sequential ramp for the choropleth (light to dark), plus the suppressed style.
RAMP = ["#deebf7", "#9ecae1", "#6baed6", "#3182bd", "#08519c"]
SUPPRESSED = "#9e9e9e"
BSA_ONLINE = "https://bsaonline.com/?uid=209"


def _norm(s) -> str:
    return " ".join(str(s or "").split()).strip()


def read_rows(path: str = SOURCE_CSV) -> list[dict]:
    """Parse the export and apply the ADR qualifying rules. Fails loud on a
    missing column or an empty file (the export already guards row counts)."""
    if not os.path.exists(path):
        raise SystemExit(f"Source not found: {path}\nRun tools/Export-BsaSales.ps1 first.")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise SystemExit(f"sales-source: missing columns {missing}")
        raw = list(reader)
    if not raw:
        raise SystemExit("sales-source: no rows")
    rows = []
    for i, r in enumerate(raw, start=2):
        try:
            price = int(float(r["price"] or 0))
            sqft = int(float(r["sqft"] or 0))
            vacant = int(float(r["vacant"] or 0))
            sold = datetime.strptime(_norm(r["saledate"]), "%Y-%m-%d").date()
        except ValueError as exc:
            raise SystemExit(f"sales-source: row {i} has a bad number or date: {exc}") from exc
        if not _norm(r["propclass"]).startswith("4"):
            continue
        if vacant or price <= 0:
            continue
        rows.append({
            "street": _norm(r["street"]),
            "city": _norm(r.get("city")) or bap.DEFAULT_CITY,
            "zip": _norm(r.get("zip")),
            "date": sold,
            "price": price,
            "sqft": sqft,
            "liberpage": _norm(r["liberpage"]),
            "lat": None,
            "lng": None,
        })
    return rows


def collapse_multi_parcel(rows: list[dict]) -> list[dict]:
    """One record per recorded sale. Rows sharing liber/page, date and price are
    the parcels of one multi-parcel sale: keep the first and drop its sqft so the
    combined price is never divided by one parcel's floor area."""
    seen: set[tuple] = set()
    dupes: set[tuple] = set()
    for r in rows:
        if not r["liberpage"]:
            continue
        key = (r["liberpage"], r["date"], r["price"])
        if key in seen:
            dupes.add(key)
        seen.add(key)
    out = []
    emitted: set[tuple] = set()
    for r in rows:
        key = (r["liberpage"], r["date"], r["price"]) if r["liberpage"] else None
        if key in emitted:
            continue
        if key is not None:
            emitted.add(key)
            if key in dupes:
                r = dict(r, sqft=0)
        out.append(r)
    return out


def geocode(rows: list[dict]) -> None:
    for i, r in enumerate(rows):
        r.update({"id": str(i), "state": bap.DEFAULT_STATE})
    cache = bap._load_cache()
    bap.geocode_batch(rows, cache)


def load_block_groups(path: str = BLOCK_GROUPS) -> list[dict]:
    import json
    with open(path, encoding="utf-8") as fh:
        fc = json.load(fh)
    return [{"geoid": f["properties"]["geoid"], "name": f["properties"]["name"],
             "geometry": f["geometry"], "rings": rings_of(f["geometry"])}
            for f in fc["features"]]


def assign(rows: list[dict], groups: list[dict]) -> tuple[dict[str, list[dict]], int]:
    """{geoid: [sales]} for geocoded rows; returns the count left unassigned."""
    by_group: dict[str, list[dict]] = defaultdict(list)
    unassigned = 0
    for r in rows:
        if r["lat"] is None or r["lng"] is None:
            unassigned += 1
            continue
        g = next((g for g in groups if contains(g["rings"], r["lng"], r["lat"])), None)
        if g is None:
            unassigned += 1
            continue
        by_group[g["geoid"]].append(r)
    return by_group, unassigned


def summarise(sales: list[dict]) -> dict:
    """Aggregate one set of sales: count, median price, median $/sqft (only when
    at least MIN_SALES carry floor area)."""
    n = len(sales)
    if n < MIN_SALES:
        return {"n": n, "median": None, "ppsf": None}
    ppsf = [s["price"] / s["sqft"] for s in sales if s["sqft"] > 0]
    return {
        "n": n,
        "median": int(statistics.median(s["price"] for s in sales)),
        "ppsf": int(round(statistics.median(ppsf))) if len(ppsf) >= MIN_SALES else None,
    }


def windows(today: date) -> tuple[date, date]:
    """(current_start, prior_start): current = [current_start, today],
    prior = [prior_start, current_start)."""
    cur = today - timedelta(days=WINDOW_DAYS)
    return cur, cur - timedelta(days=WINDOW_DAYS)


def group_stats(by_group: dict[str, list[dict]], groups: list[dict], today: date) -> list[dict]:
    cur_start, prior_start = windows(today)
    out = []
    for g in groups:
        sales = by_group.get(g["geoid"], [])
        cur = summarise([s for s in sales if s["date"] >= cur_start])
        prior = summarise([s for s in sales if prior_start <= s["date"] < cur_start])
        change = None
        if cur["median"] and prior["median"]:
            change = round((cur["median"] - prior["median"]) / prior["median"] * 100)
        out.append({"geoid": g["geoid"], "name": g["name"], "geometry": g["geometry"],
                    "cur": cur, "prior": prior, "change": change})
    return out


def _money(n: int | None) -> str:
    return f"${n:,}" if n is not None else "n/a"


def _count_label(n: int) -> str:
    if n >= MIN_SALES:
        return str(n)
    return "0" if n == 0 else f"1 to {MIN_SALES - 1}"


def _change_label(change: int | None) -> str:
    if change is None:
        return "n/a"
    return f"{change:+d}%"


def color_for(median: int | None, breaks: list[int]) -> str:
    if median is None:
        return SUPPRESSED
    idx = sum(1 for b in breaks if median > b)
    return RAMP[min(idx, len(RAMP) - 1)]


def ramp_breaks(stats: list[dict]) -> list[int]:
    """Four quantile breaks over the shown medians (five classes)."""
    meds = sorted(s["cur"]["median"] for s in stats if s["cur"]["median"] is not None)
    if len(meds) < len(RAMP):
        return meds[:-1] if len(meds) > 1 else []
    return [meds[int(len(meds) * k / len(RAMP))] for k in range(1, len(RAMP))]


def build_geojson(stats: list[dict], today: date) -> dict:
    breaks = ramp_breaks(stats)
    cur_start, _ = windows(today)
    period = f"{cur_start.strftime('%b %Y')} to {today.strftime('%b %Y')}"
    features = []
    for s in stats:
        cur = s["cur"]
        shown = cur["median"] is not None
        rows = [["Arms-length home sales", f"{_count_label(cur['n'])} ({period})"]]
        if shown:
            rows.append(["Median sale price", _money(cur["median"])])
            rows.append(["Median price per sq ft", _money(cur["ppsf"]) if cur["ppsf"] else "n/a"])
            rows.append(["Change vs prior 24 months", _change_label(s["change"])])
        else:
            rows.append(["Median sale price", f"Not shown: fewer than {MIN_SALES} sales"])
        features.append({
            "type": "Feature",
            "geometry": s["geometry"],
            "properties": {
                "name": s["name"],
                "geoid": s["geoid"],
                "sales": cur["n"] if shown else None,
                "median": cur["median"],
                "ppsf": cur["ppsf"],
                "_color": color_for(cur["median"], breaks),
                "_weight": 1.5,
                "_fillOpacity": 0.55 if shown else 0.12,
                "_popupRows": rows,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def half_year_series(rows: list[dict]) -> list[dict]:
    """Citywide median price per half-year over the four-year export."""
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for r in rows:
        buckets[(r["date"].year, 1 if r["date"].month <= 6 else 2)].append(r["price"])
    pts = []
    for (y, h), prices in sorted(buckets.items()):
        if len(prices) >= MIN_SALES:
            pts.append({"x": f"{y} H{h}", "y": int(statistics.median(prices))})
    return pts


def build_panel(rows: list[dict], stats: list[dict], unassigned: int, today: date) -> dict:
    cur_start, prior_start = windows(today)
    cur_rows = [r for r in rows if r["date"] >= cur_start]
    prior_rows = [r for r in rows if prior_start <= r["date"] < cur_start]
    city_cur = summarise(cur_rows)
    city_prior = summarise(prior_rows)
    change = None
    if city_cur["median"] and city_prior["median"]:
        change = round((city_cur["median"] - city_prior["median"]) / city_prior["median"] * 100)
    shown = [s for s in stats if s["cur"]["median"] is not None]
    period = f"{cur_start.strftime('%B %Y')} to {today.strftime('%B %Y')}"

    stats_out = [
        {"label": "Arms-length home sales, last 24 months", "value": f"{city_cur['n']:,}",
         "hint": period},
        {"label": "Citywide median sale price", "value": _money(city_cur["median"]),
         "hint": "half the homes sold for less, half for more"},
        {"label": "Citywide median price per sq ft", "value": _money(city_cur["ppsf"]),
         "hint": "finished floor area from the Assessing record"},
        {"label": "Change vs the prior 24 months", "value": _change_label(change),
         "hint": f"prior median {_money(city_prior['median'])}"},
        {"label": "Neighbourhoods with a shown price", "value": f"{len(shown)} of {len(stats)}",
         "hint": f"block groups with at least {MIN_SALES} sales"},
    ]

    bands = [(0, 100_000, "Under $100k"), (100_000, 150_000, "$100k to $150k"),
             (150_000, 200_000, "$150k to $200k"), (200_000, 300_000, "$200k to $300k"),
             (300_000, 10**9, "$300k and up")]
    band_series = [{"label": label, "value": sum(1 for r in cur_rows if lo <= r["price"] < hi)}
                   for lo, hi, label in bands]

    charts = [
        {"type": "trend", "title": "Citywide median sale price by half-year",
         "unit": "$", "points": half_year_series(rows)},
        {"type": "bars", "title": "Home sales by price, last 24 months", "series": band_series},
    ]

    table_rows = []
    for s in sorted(stats, key=lambda s: (s["cur"]["median"] is None, -(s["cur"]["median"] or 0))):
        cur = s["cur"]
        table_rows.append({"cells": [
            s["name"], _count_label(cur["n"]), _money(cur["median"]),
            _money(cur["ppsf"]), _change_label(s["change"]),
        ]})
    tables = [{
        "title": "Sale prices by neighbourhood (Census block group), last 24 months",
        "columns": ["Block group", "Sales", "Median price", "Median $/sq ft", "Change vs prior 24 months"],
        "rows": table_rows,
    }]

    notes = [
        f"Turn on the \"Home sale prices (by block group)\" map overlay. Darker blue is a higher median; grey means fewer than {MIN_SALES} sales, so no price is shown.",
        "Only arms-length sales count: transfers the City Assessor codes as open-market sales between unrelated parties, improved homes only, with a recorded price. Family transfers, foreclosures, short sales, land contracts and bare lots are excluded.",
        "Figures are aggregates. No individual sale, address or price is published. Sale prices are public record and can be looked up per parcel on BS&A Online.",
        f"{unassigned} qualifying sales could not be placed in a block group (address not geocoded) and are left out of every figure.",
    ]
    return {
        "title": "Home Sale Prices",
        "subtitle": "What homes in Burton actually sell for, by neighbourhood, from the City Assessor's sales records",
        "lastUpdated": today.isoformat(),
        "stats": stats_out,
        "charts": charts,
        "tables": tables,
        "source": "City of Burton Assessor sales records (BS&A), arms-length residential sales, aggregated by Census block group. Block-group boundaries from the U.S. Census Bureau (TIGERweb).",
        "links": [
            {"text": "Look up a parcel on BS&A Online", "href": BSA_ONLINE},
            {"text": "Burton Assessor's Office", "href": "https://www.burtonmi.gov/government/assessor2/index.php"},
        ],
        "notes": notes,
    }


def main() -> int:
    today = date.today()
    rows = collapse_multi_parcel(read_rows())
    print(f"Read {len(rows)} qualifying sales from {os.path.basename(SOURCE_CSV)}")
    geocode(rows)
    groups = load_block_groups()
    by_group, unassigned = assign(rows, groups)
    placed = sum(len(v) for v in by_group.values())
    stats = group_stats(by_group, groups, today)
    placed_rows = [r for v in by_group.values() for r in v]
    write_geojson(OUT_GEOJSON, build_geojson(stats, today))
    write_json(OUT_INFO, build_panel(placed_rows, stats, unassigned, today))
    shown = sum(1 for s in stats if s["cur"]["median"] is not None)
    print(f"Placed {placed} sales in {len(groups)} block groups ({unassigned} unplaced); "
          f"{shown} groups show a value -> {os.path.basename(OUT_GEOJSON)}, {os.path.basename(OUT_INFO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
