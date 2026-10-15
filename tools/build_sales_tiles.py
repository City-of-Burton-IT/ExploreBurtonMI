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
import json
from lib.iox import write_geojson, write_json
from lib.paths import pipeline_data_path, public_path

SOURCE_CSV = pipeline_data_path("sales-source.csv")
CENTROIDS_CSV = pipeline_data_path("parcel-centroids.csv")  # optional, from extract_parcel_centroids.py
BLOCK_GROUPS = public_path("block-groups.geojson")
SCHOOL_DISTRICTS = public_path("school-districts.geojson")
PROPERTY_TAX = public_path("info-propertytax.json")
ACS_BLOCKGROUPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "data", "acs-blockgroups.json")
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
            "parcel": _norm(r.get("parcel")),
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


def read_centroids(path: str = CENTROIDS_CSV) -> dict[str, tuple[float, float]]:
    """{parcel: (lat, lng)} from the City parcel map, or {} when the file is absent."""
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return {r["parcel"]: (float(r["lat"]), float(r["lng"])) for r in csv.DictReader(fh)}


def geocode(rows: list[dict], centroids: dict[str, tuple[float, float]] | None = None) -> int:
    """Place each sale: parcel centroid first (exact lot), the Census geocoder for
    the rest. Returns how many came from centroids."""
    hit = 0
    for i, r in enumerate(rows):
        r.update({"id": str(i), "state": bap.DEFAULT_STATE})
        c = (centroids or {}).get(r.get("parcel", ""))
        if c:
            r["lat"], r["lng"] = c
            hit += 1
    cache = bap._load_cache()
    bap.geocode_batch([r for r in rows if r["lat"] is None], cache)
    return hit


def load_block_groups(path: str = BLOCK_GROUPS) -> list[dict]:
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


def load_tax_context(districts_path: str = SCHOOL_DISTRICTS, tax_path: str = PROPERTY_TAX) -> dict:
    """School-district polygons plus the Property Taxes estimator rates, so each
    block group can carry an estimated tax bill on its median home."""
    with open(districts_path, encoding="utf-8") as fh:
        sd = json.load(fh)
    with open(tax_path, encoding="utf-8") as fh:
        est = json.load(fh).get("estimator") or {}
    district_mills = {d["name"]: float(d["homestead"]) for d in est.get("districts", [])}
    districts = []
    for f in sd.get("features", []):
        name = f["properties"].get("name", "")
        short = next((k for k in district_mills if name.upper().startswith(k.upper())), None)
        districts.append({"name": name, "short": short, "rings": rings_of(f["geometry"])})
    return {"districts": districts, "city_mills": float(est.get("cityMills") or 0),
            "district_mills": district_mills}


def district_for(sales: list[dict], ctx: dict) -> dict | None:
    """The school district containing the block group's sales centroid (block
    groups and districts do not nest, so this is 'mostly in'), or None."""
    if not sales or not ctx.get("districts"):
        return None
    lat = statistics.mean(s["lat"] for s in sales)
    lng = statistics.mean(s["lng"] for s in sales)
    return next((d for d in ctx["districts"] if contains(d["rings"], lng, lat)), None)


def tax_estimate(median: int | None, district: dict | None, ctx: dict) -> dict:
    """Estimated annual tax on a home bought at the median price. Michigan
    uncaps taxable value on sale to 50% of market value, so taxable = price / 2.
    City tax uses the City's own mills; the full homestead bill uses the
    district's published total homestead rate (schools, county, City, etc.)."""
    if not median or not ctx.get("city_mills"):
        return {"taxable": None, "city": None, "full": None}
    taxable = median / 2
    city = round(taxable * ctx["city_mills"] / 1000)
    full = None
    if district and district.get("short") and district["short"] in ctx["district_mills"]:
        full = round(taxable * ctx["district_mills"][district["short"]] / 1000)
    return {"taxable": round(taxable), "city": city, "full": full}


def load_acs(path: str = ACS_BLOCKGROUPS) -> dict:
    """{"vintage": str, "rows": {geoid: record}} from fetch_blockgroup_housing.py,
    or an empty dict when the file is absent (the panel then omits that context)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return {"vintage": d.get("vintage", ""), "source": d.get("source", ""),
            "rows": {r["geoid"]: r for r in d.get("rows", [])}}


def _pct(v: int | None) -> str:
    return f"{v}%" if v is not None else "n/a"


def _weak(value: int | None, moe: int | None) -> bool:
    """A block-group estimate whose margin of error exceeds half the value is
    too noisy to quote without a flag."""
    return bool(value and moe and moe > value / 2)


def short_district(name: str | None) -> str:
    if not name:
        return "n/a"
    for suffix in (" Community School District", " Community Schools", " Public Schools"):
        name = name.replace(suffix, "")
    return name


def group_stats(by_group: dict[str, list[dict]], groups: list[dict], today: date,
                ctx: dict | None = None) -> list[dict]:
    cur_start, prior_start = windows(today)
    ctx = ctx or {}
    out = []
    for g in groups:
        sales = by_group.get(g["geoid"], [])
        cur = summarise([s for s in sales if s["date"] >= cur_start])
        prior = summarise([s for s in sales if prior_start <= s["date"] < cur_start])
        change = None
        if cur["median"] and prior["median"]:
            change = round((cur["median"] - prior["median"]) / prior["median"] * 100)
        district = district_for(sales, ctx)
        out.append({"geoid": g["geoid"], "name": g["name"], "geometry": g["geometry"],
                    "cur": cur, "prior": prior, "change": change,
                    "district": district["name"] if district else None,
                    "tax": tax_estimate(cur["median"], district, ctx),
                    "acs": (ctx.get("acs") or {}).get("rows", {}).get(g["geoid"])})
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
            tax = s.get("tax") or {}
            if tax.get("city"):
                rows.append(["Est. City tax on the median home", f"{_money(tax['city'])} a year"])
            if tax.get("full"):
                rows.append(["Est. full tax bill (homestead)", f"{_money(tax['full'])} a year"])
        else:
            rows.append(["Median sale price", f"Not shown: fewer than {MIN_SALES} sales"])
        if s.get("district"):
            rows.append(["School district", s["district"]])
        a = s.get("acs") or {}
        if a:
            if a.get("owner_share") is not None:
                rows.append(["Owner-occupied homes", f"{a['owner_share']}% (Census ACS)"])
            if a.get("median_rent"):
                rows.append(["Median rent", _money(a["median_rent"]) + " a month" + (" (wide margin)" if _weak(a["median_rent"], a.get("median_rent_moe")) else "")])
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


def build_panel(rows: list[dict], stats: list[dict], unassigned: int, today: date,
                ctx: dict | None = None) -> dict:
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
    ctx = ctx or {}
    city_tax = tax_estimate(city_cur["median"], None, ctx)
    if city_tax["city"]:
        stats_out.insert(3, {"label": "Est. City tax on the median home", "value": f"{_money(city_tax['city'])} a year",
                             "hint": f"taxable value {_money(city_tax['taxable'])} at {ctx.get('city_mills', 0):.2f} City mills"})

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
        tax = s.get("tax") or {}
        table_rows.append({"cells": [
            s["name"], short_district(s.get("district")), _count_label(cur["n"]), _money(cur["median"]),
            _money(cur["ppsf"]), _change_label(s["change"]), _money(tax.get("city")), _money(tax.get("full")),
        ]})
    acs = (ctx or {}).get("acs") or {}
    acs_rows = []
    if acs.get("rows"):
        for s in sorted(stats, key=lambda s: s["name"]):
            a = s.get("acs") or {}
            if not a:
                continue
            rent = _money(a.get("median_rent")) + (" *" if _weak(a.get("median_rent"), a.get("median_rent_moe")) else "")
            value = _money(a.get("median_value")) + (" *" if _weak(a.get("median_value"), a.get("median_value_moe")) else "")
            acs_rows.append({"cells": [s["name"], _pct(a.get("owner_share")), _pct(a.get("vacancy_rate")),
                                       rent, value]})
    tables = [{
        "title": "Sale prices by neighbourhood (Census block group), last 24 months",
        "columns": ["Block group", "School district", "Sales", "Median price", "Median $/sq ft",
                    "Change vs prior 24 months", "Est. City tax on median home", "Est. full tax bill"],
        "rows": table_rows,
    }]
    if acs_rows:
        tables.append({
            "title": f"Who lives here: Census profile by block group (ACS {acs.get('vintage', '')})",
            "columns": ["Block group", "Owner-occupied", "Vacant units", "Median rent", "Median value (ACS)"],
            "rows": acs_rows,
        })

    notes = [
        f"Turn on the \"Home sale prices (by block group)\" map overlay. Darker blue is a higher median; grey means fewer than {MIN_SALES} sales, so no price is shown.",
        "Only arms-length sales count: transfers the City Assessor codes as open-market sales between unrelated parties, improved homes only, with a recorded price. Family transfers, foreclosures, short sales, land contracts and bare lots are excluded.",
        "Figures are aggregates. No individual sale, address or price is published. Sale prices are public record and can be looked up per parcel on BS&A Online.",
        f"{unassigned} qualifying sales could not be placed in a block group (address not geocoded) and are left out of every figure.",
        "Tax estimates assume a home bought at the median price: Michigan sets taxable value to half the sale price in the year after a sale. The City figure uses the City's own millage; the full bill uses the school district's published total homestead rate and is an estimate before any exemption. See the Property Taxes dashboard for the estimator.",
        "The school district shown is the one containing most of the block group; a few block groups straddle two districts.",
    ]
    if acs_rows:
        notes.append(f"The Census profile is the American Community Survey {acs.get('vintage', '')} five-year estimate, a survey with wide margins at block-group level; a value marked * has a margin of error above half the estimate. The ACS median value is what owners say their home is worth, not a sale price.")
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
    hit = geocode(rows, read_centroids())
    print(f"  {hit} sales placed from parcel centroids, the rest geocoded by address")
    groups = load_block_groups()
    by_group, unassigned = assign(rows, groups)
    placed = sum(len(v) for v in by_group.values())
    ctx = load_tax_context()
    ctx["acs"] = load_acs()
    stats = group_stats(by_group, groups, today, ctx)
    placed_rows = [r for v in by_group.values() for r in v]
    write_geojson(OUT_GEOJSON, build_geojson(stats, today))
    write_json(OUT_INFO, build_panel(placed_rows, stats, unassigned, today, ctx))
    shown = sum(1 for s in stats if s["cur"]["median"] is not None)
    print(f"Placed {placed} sales in {len(groups)} block groups ({unassigned} unplaced); "
          f"{shown} groups show a value -> {os.path.basename(OUT_GEOJSON)}, {os.path.basename(OUT_INFO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
