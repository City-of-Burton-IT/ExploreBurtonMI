"""Fetch a demographics snapshot for the City of Burton from the US Census ACS
5-year API and write public/info-demographics.json in the InfoPanel schema.

Re-runnable annually:
    set CENSUS_API_KEY=...        (or pass --key)
    python tools/fetch_census.py [--year 2023]

A free Census API key is required (the API now rejects keyless requests):
    https://api.census.gov/data/key_signup.html

Stdlib only (urllib) -- no dependencies, matching the other tools/ scripts. The
output is committed; the public site reads the JSON, never the Census API.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

STATE_FIPS = "26"        # Michigan
PLACE_FIPS = "12060"     # Burton city (GEOID 2612060; verified via data.census.gov)
EXPECTED_NAME_PREFIX = "Burton city"

# Income brackets (B19001) grouped into 5 readable buckets.
INCOME_GROUPS = [
    ("< $25k", ["002", "003", "004", "005"]),
    ("$25-50k", ["006", "007", "008", "009", "010"]),
    ("$50-75k", ["011", "012"]),
    ("$75-100k", ["013"]),
    ("$100k+", ["014", "015", "016", "017"]),
]

CORE_VARS = {
    "population": "B01003_001E",
    "median_age": "B01002_001E",
    "households": "B11001_001E",
    "median_income": "B19013_001E",
    "median_home_value": "B25077_001E",
    "tenure_total": "B25003_001E",
    "owner": "B25003_002E",
    "renter": "B25003_003E",
}


def _income_vars() -> list[str]:
    return [f"B19001_{n}E" for _, codes in INCOME_GROUPS for n in codes]


def fetch(year: int, key: str) -> dict:
    get_vars = ["NAME", *CORE_VARS.values(), *_income_vars()]
    url = (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get={','.join(get_vars)}&for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}&key={key}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        rows = json.load(resp)
    header, values = rows[0], rows[1]
    record = dict(zip(header, values))
    name = record.get("NAME", "")
    if not name.startswith(EXPECTED_NAME_PREFIX):
        raise SystemExit(f"Unexpected place NAME from Census: {name!r} (check FIPS codes)")
    return record


def _int(record: dict, key: str) -> int:
    raw = record.get(key)
    val = int(float(raw)) if raw not in (None, "") else 0
    return val if val >= 0 else 0  # Census uses large negatives for null


def build_panel(record: dict, year: int) -> dict:
    population = _int(record, CORE_VARS["population"])
    median_age = float(record[CORE_VARS["median_age"]])
    households = _int(record, CORE_VARS["households"])
    median_income = _int(record, CORE_VARS["median_income"])
    median_home_value = _int(record, CORE_VARS["median_home_value"])
    owner = _int(record, CORE_VARS["owner"])
    renter = _int(record, CORE_VARS["renter"])
    owner_pct = round(owner / (owner + renter) * 100) if (owner + renter) else 0

    income_series = []
    for label, codes in INCOME_GROUPS:
        total = sum(_int(record, f"B19001_{n}E") for n in codes)
        income_series.append({"label": label, "value": total})

    return {
        "title": "Burton Demographics",
        "subtitle": f"U.S. Census ACS {year} 5-year estimates",
        "stats": [
            {"label": "Population", "value": f"{population:,}"},
            {"label": "Median age", "value": f"{median_age:.1f}"},
            {"label": "Households", "value": f"{households:,}"},
            {"label": "Median household income", "value": f"${median_income:,}"},
            {"label": "Median home value", "value": f"${median_home_value:,}"},
            {"label": "Owner-occupied homes", "value": f"{owner_pct}%"},
        ],
        "charts": [
            {
                "type": "donut",
                "title": "Housing tenure",
                "series": [
                    {"label": "Owner-occupied", "value": owner},
                    {"label": "Renter-occupied", "value": renter},
                ],
            },
            {
                "type": "bars",
                "title": "Households by income",
                "series": income_series,
            },
        ],
        "source": f"U.S. Census Bureau, American Community Survey {year} 5-year estimates",
        "links": [
            {
                "text": "Census QuickFacts: Burton city, MI",
                "href": "https://www.census.gov/quickfacts/burtoncitymichigan",
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Burton demographics from the Census ACS.")
    parser.add_argument("--year", type=int, default=2023, help="ACS 5-year vintage (default 2023)")
    parser.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"), help="Census API key (or set CENSUS_API_KEY)")
    args = parser.parse_args()

    if not args.key:
        raise SystemExit(
            "A Census API key is required. Get a free key at\n"
            "  https://api.census.gov/data/key_signup.html\n"
            "then set CENSUS_API_KEY or pass --key."
        )

    try:
        record = fetch(args.year, args.key)
    except Exception as exc:  # noqa: BLE001 - report and try a fallback year
        print(f"  {args.year} ACS5 fetch failed ({exc}); retrying {args.year - 1} ...")
        record = fetch(args.year - 1, args.key)
        args.year -= 1

    panel = build_panel(record, args.year)
    out = os.path.join(os.path.dirname(__file__), "..", "public", "info-demographics.json")
    out = os.path.abspath(out)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {out}")
    print(f"  population={panel['stats'][0]['value']}  median income={panel['stats'][3]['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
