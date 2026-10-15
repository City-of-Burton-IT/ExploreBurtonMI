"""Fetch ACS 5-year housing context for Burton's Census block groups and write
tools/data/acs-blockgroups.json (committed; Census data is public domain).

Read by tools/build_sales_tiles.py to add "who lives here" context next to sale
prices: owner-occupied share, vacancy rate, median gross rent, ACS median home
value, per block group. (Mean commute was tried and is not
published at block-group level, so it is not fetched.) Block-group ACS estimates carry
wide margins of error; the output keeps each margin so the dashboard can mark
weak estimates, and the builder shows "n/a" where the Census suppresses a value.

Requires CENSUS_API_KEY (user environment variable; never committed).
    pipeline/.venv/Scripts/python tools/fetch_blockgroup_housing.py [--year 2023]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import REPO_ROOT, public_path

BLOCK_GROUPS = public_path("block-groups.geojson")
OUT = os.path.join(REPO_ROOT, "tools", "data", "acs-blockgroups.json")
STATE, COUNTY = "26", "049"

# variable -> key. *M variants are margins of error (90% confidence).
VARS = {
    "B25003_001E": "occupied", "B25003_002E": "owner_occupied",
    "B25002_001E": "units", "B25002_003E": "vacant",
    "B25064_001E": "median_rent", "B25064_001M": "median_rent_moe",
    "B25077_001E": "median_value", "B25077_001M": "median_value_moe",
}


def _num(v) -> float | None:
    """Census returns strings; negative sentinel values mean suppressed/NA."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f < 0 else f


def fetch(year: int, key: str) -> list[dict]:
    url = (f"https://api.census.gov/data/{year}/acs/acs5?get=" + ",".join(VARS)
           + f"&for=block%20group:*&in=state:{STATE}%20county:{COUNTY}%20tract:*&key={key}")
    rows = get_json(url, timeout=60)
    if not rows or len(rows) < 2:
        raise SystemExit("Census API returned no block-group rows")
    header, data = rows[0], rows[1:]
    out = []
    for r in data:
        rec = dict(zip(header, r))
        geoid = rec["state"] + rec["county"] + rec["tract"] + rec["block group"]
        out.append({"geoid": geoid, **{VARS[k]: _num(rec.get(k)) for k in VARS}})
    return out


def derive(rec: dict) -> dict:
    """Shares and means from the raw counts; None where the denominator is 0/NA."""
    occ, own = rec.get("occupied"), rec.get("owner_occupied")
    units, vac = rec.get("units"), rec.get("vacant")
    return {
        "geoid": rec["geoid"],
        "owner_share": round(own / occ * 100) if occ and own is not None else None,
        "vacancy_rate": round(vac / units * 100) if units and vac is not None else None,
        "median_rent": int(rec["median_rent"]) if rec.get("median_rent") else None,
        "median_rent_moe": int(rec["median_rent_moe"]) if rec.get("median_rent_moe") else None,
        "median_value": int(rec["median_value"]) if rec.get("median_value") else None,
        "median_value_moe": int(rec["median_value_moe"]) if rec.get("median_value_moe") else None,
        "housing_units": int(units) if units else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023, help="ACS 5-year vintage end year")
    ap.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"))
    args = ap.parse_args()
    if not args.key:
        sys.exit("Census API key required: set CENSUS_API_KEY or pass --key.")
    with open(BLOCK_GROUPS, encoding="utf-8") as fh:
        wanted = {f["properties"]["geoid"] for f in json.load(fh)["features"]}
    county = fetch(args.year, args.key)
    rows = [derive(r) for r in county if r["geoid"] in wanted]
    missing = wanted - {r["geoid"] for r in rows}
    if missing:
        print(f"  WARNING: {len(missing)} Burton block groups not in the ACS response: {sorted(missing)}")
    if len(rows) < len(wanted) * 0.8:
        raise SystemExit("Fewer than 80% of Burton block groups matched; vintage or geography changed?")
    write_json(OUT, {
        "source": f"U.S. Census Bureau, ACS 5-year {args.year - 4}-{args.year}, tables B25003, B25002, B25064, B25077",
        "vintage": f"{args.year - 4}-{args.year}",
        "fetched": date.today().isoformat(),
        "rows": sorted(rows, key=lambda r: r["geoid"]),
    })
    print(f"Wrote {len(rows)} block groups (ACS {args.year}) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
