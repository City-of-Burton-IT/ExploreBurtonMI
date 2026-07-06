# Build public/info-housing.json for the Housing & Growth dashboard.
#
# Source: US Census American Community Survey (ACS) 5-year, place-level for
# Burton city, Michigan (state 26, place 12060 / GEOID 2612060). A free Census
# API key is required (env CENSUS_API_KEY or --key); the key is NEVER committed.
# Public, redistributable with the Census ToS notice (rendered in notes).
#
# Complements the Demographics dashboard (which carries tenure) by focusing on
# the housing stock itself: units, value, rent, age of homes, vacancy.
#
# Re-runnable annually (committed output; the site reads the JSON, never the API):
#   CENSUS_API_KEY=... python tools/fetch_housing.py [--year 2023]
#
# Uses the shared tools/lib helpers (HTTP retry, atomic writes).
from __future__ import annotations

import argparse
import os
import sys

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

STATE_FIPS = "26"        # Michigan
PLACE_FIPS = "12060"     # Burton city (GEOID 2612060)
OUT = public_path("info-housing.json")

# B25034 Year Structure Built -> bucket label (newest first for the chart).
YEAR_BUILT = [
    ("B25034_002E", "2020 or later"),
    ("B25034_003E", "2010-2019"),
    ("B25034_004E", "2000-2009"),
    ("B25034_005E", "1990-1999"),
    ("B25034_006E", "1980-1989"),
    ("B25034_007E", "1970-1979"),
    ("B25034_008E", "1960-1969"),
    ("B25034_009E", "1950-1959"),
    ("B25034_010E", "1940-1949"),
    ("B25034_011E", "1939 or earlier"),
]
CORE = ["NAME", "B25001_001E", "B25002_003E", "B25003_001E", "B25003_002E",
        "B25003_003E", "B25077_001E", "B25064_001E", "B25035_001E"]


def _fetch(year: int, key: str, get_vars: list[str]) -> dict:
    url = (f"https://api.census.gov/data/{year}/acs/acs5"
           f"?get={','.join(get_vars)}&for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}&key={key}")
    rows = get_json(url, timeout=40)
    return dict(zip(rows[0], rows[1]))


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=2023, help="ACS 5-year end year")
    ap.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"))
    args = ap.parse_args()
    if not args.key:
        sys.exit("Census API key required: set CENSUS_API_KEY or pass --key. "
                 "Free signup: https://api.census.gov/data/key_signup.html")

    core = _fetch(args.year, args.key, CORE)
    if "burton" not in str(core.get("NAME", "")).lower():
        sys.exit(f"Unexpected place NAME: {core.get('NAME')!r} (check FIPS codes)")
    yb = _fetch(args.year, args.key, ["NAME"] + [c for c, _ in YEAR_BUILT])

    total = _int(core["B25001_001E"])
    vacant = _int(core["B25002_003E"])
    occupied = _int(core["B25003_001E"])
    owner = _int(core["B25003_002E"])
    renter = _int(core["B25003_003E"])
    value = _int(core["B25077_001E"])
    rent = _int(core["B25064_001E"])
    med_built = _int(core["B25035_001E"])
    own_rate = round(100 * owner / occupied, 1) if occupied else 0
    vac_rate = round(100 * vacant / total, 1) if total else 0

    stats = [
        {"label": "Housing units", "value": f"{total:,}", "hint": f"ACS {args.year}"},
        {"label": "Owner-occupied", "value": f"{own_rate}%",
         "hint": f"{owner:,} of {occupied:,} occupied"},
        {"label": "Median home value", "value": f"${value:,}"},
        {"label": "Median gross rent", "value": f"${rent:,}/mo"},
        {"label": "Median year built", "value": str(med_built)},
        {"label": "Vacancy rate", "value": f"{vac_rate}%", "hint": f"{vacant:,} units"},
    ]
    charts = [
        {"type": "donut", "title": "Owner vs. renter (occupied homes)",
         "series": [{"label": "Owner-occupied", "value": owner},
                    {"label": "Renter-occupied", "value": renter}]},
        {"type": "bars", "title": "Homes by decade built", "unit": "",
         "series": [{"label": lab, "value": _int(yb[code])} for code, lab in YEAR_BUILT]},
    ]
    # Median home value + gross rent trends (non-overlapping ACS 5-year windows).
    value_pts, rent_pts = [], []
    for yr in (2013, 2018, args.year):
        try:
            t = _fetch(yr, args.key, ["B25077_001E", "B25064_001E"])
        except Exception as e:  # noqa: BLE001 - skip a year the API can't serve
            print(f"  housing trend {yr} skipped ({e})")
            continue
        v, r = _int(t["B25077_001E"]), _int(t["B25064_001E"])
        if v > 0:
            value_pts.append({"x": str(yr), "y": v})
        if r > 0:
            rent_pts.append({"x": str(yr), "y": r})
    if len(value_pts) >= 2:
        charts.append({"type": "trend", "title": "Median home value ($)", "unit": "$", "points": value_pts})
    if len(rent_pts) >= 2:
        charts.append({"type": "trend", "title": "Median gross rent ($/mo)", "unit": "$", "points": rent_pts})

    panel = {
        "title": "Housing & Growth",
        "subtitle": f"Burton's housing stock: US Census ACS {args.year} 5-year",
        "stats": stats,
        "charts": charts,
        "source": f"US Census Bureau, American Community Survey (ACS) {args.year} "
                  f"5-year estimates, Burton city, Michigan.",
        "links": [{"text": "Census QuickFacts: Burton",
                   "href": "https://www.census.gov/quickfacts/burtoncitymichigan"}],
        "notes": [
            "Figures are ACS model-based estimates (5-year averages), not exact counts. "
            "Trend points use non-overlapping 5-year windows (2009-2013, 2014-2018, 2019-2023) "
            "and are nominal dollars (not inflation-adjusted).",
            "This product uses the Census Bureau Data API but is not endorsed or "
            "certified by the Census Bureau.",
        ],
    }
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  units={total:,} own_rate={own_rate}% value=${value:,} rent=${rent} "
          f"built={med_built} vacancy={vac_rate}%")
    print(f"  by decade: " + ", ".join(f"{lab}={_int(yb[c])}" for c, lab in YEAR_BUILT))


if __name__ == "__main__":
    main()
