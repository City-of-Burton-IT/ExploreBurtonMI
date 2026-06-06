"""Fetch a demographics snapshot for the City of Burton from the US Census ACS
5-year API (plus decennial counts for the population trend) and write
public/info-demographics.json in the InfoPanel schema.

Re-runnable annually:
    set CENSUS_API_KEY=...        (or pass --key)
    python tools/fetch_census.py [--year 2023]

A free Census API key is required (the API now rejects keyless requests):
    https://api.census.gov/data/key_signup.html

Census API Terms of Service require the notice "This product uses the Census
Bureau Data API but is not endorsed or certified by the Census Bureau" be
displayed prominently; it is emitted into the panel's `notes` and rendered in the
app footer.

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
COUNTY_FIPS = "049"      # Genesee County (Burton's county)
EXPECTED_NAME_PREFIX = "Burton city"

# Bachelor's-or-higher components of B15003 (for the benchmark comparison).
BACHELOR_CODES = ["022", "023", "024", "025"]

# Metrics shown in the "How Burton compares" panel (Burton vs County vs State).
# (label, unit, metric key from _metrics()).
COMPARE_SPECS = [
    ("Median household income", "$", "median_income"),
    ("Median home value", "$", "median_home_value"),
    ("Owner-occupied homes", "%", "owner_pct"),
    ("Bachelor's degree or higher", "%", "bachelors_pct"),
    ("Below poverty line", "%", "poverty_pct"),
    ("Unemployment rate", "%", "unemployment_pct"),
    ("Median age", "", "median_age"),
]

# --- ACS table variable groupings -----------------------------------------
# Variable codes verified against https://api.census.gov/data/<year>/acs/acs5/groups/<TABLE>.json

# Income brackets (B19001) grouped into 5 readable buckets.
INCOME_GROUPS = [
    ("< $25k", ["002", "003", "004", "005"]),
    ("$25-50k", ["006", "007", "008", "009", "010"]),
    ("$50-75k", ["011", "012"]),
    ("$75-100k", ["013"]),
    ("$100k+", ["014", "015", "016", "017"]),
]

# Educational attainment (B15003, population 25+) collapsed to 5 levels.
EDU_GROUPS = [
    ("No diploma", [f"{n:03d}" for n in range(2, 17)]),   # 002-016: none .. 12th no diploma
    ("High school / GED", ["017", "018"]),
    ("Some college / associate", ["019", "020", "021"]),
    ("Bachelor's degree", ["022"]),
    ("Graduate / professional", ["023", "024", "025"]),
]

# Means of transportation to work (B08301). Partition sums to the table total (001).
COMMUTE_GROUPS = [
    ("Drove alone", ["003"]),
    ("Carpooled", ["004"]),
    ("Public transit", ["010"]),
    ("Walked / bicycled", ["018", "019"]),
    ("Worked from home", ["021"]),
    ("Other", ["016", "017", "020"]),   # taxicab, motorcycle, other means
]

# Sex by age (B01001) collapsed to 5 bands (male + female codes summed per band).
AGE_BANDS = [
    ("Under 18", ["003", "004", "005", "006", "027", "028", "029", "030"]),
    ("18-34", ["007", "008", "009", "010", "011", "012",
               "031", "032", "033", "034", "035", "036"]),
    ("35-54", ["013", "014", "015", "016", "037", "038", "039", "040"]),
    ("55-64", ["017", "018", "019", "041", "042", "043"]),
    ("65+", ["020", "021", "022", "023", "024", "025",
             "044", "045", "046", "047", "048", "049"]),
]

# Single-value ACS variables.
CORE_VARS = {
    "population": "B01003_001E",
    "median_age": "B01002_001E",
    "households": "B11001_001E",
    "median_income": "B19013_001E",
    "median_home_value": "B25077_001E",
    "owner": "B25003_002E",
    "renter": "B25003_003E",
    # Educational attainment denominator (pop 25+)
    "edu_total": "B15003_001E",
    # Employment status (B23025)
    "pop_16plus": "B23025_001E",
    "in_labor_force": "B23025_002E",
    "civilian_labor_force": "B23025_003E",
    "employed": "B23025_004E",
    "unemployed": "B23025_005E",
    # Poverty status (B17001)
    "poverty_total": "B17001_001E",
    "poverty_below": "B17001_002E",
    # Veteran status (B21001, civilian pop 18+)
    "vet_total": "B21001_001E",
    "veterans": "B21001_002E",
}

# Decennial population counts for the trend (place 12060, state 26).
# ACS 5-year vintages overlap and MUST NOT be charted year-over-year; decennial
# counts are non-overlapping actual counts, the Census-recommended comparison.
DECENNIAL = [
    ("2000", "2000/dec/sf1", "P001001"),
    ("2010", "2010/dec/sf1", "P001001"),
    ("2020", "2020/dec/pl", "P1_001N"),
]

# Homeownership-rate trend from the decennial tenure tables. Variable names verified
# against each dataset's group JSON (they differ by vintage):
#   2000 sf1 H4:  H004001 total occupied, H004002 owner occupied
#   2010 sf1 H4:  H004001 total, owner = H004002 (w/ mortgage) + H004003 (free & clear)
#   2020 dhc H10: H10_001N total, H10_002N owner occupied
# (dataset, total_var, [owner_vars]) -- owner counts are summed.
TENURE_SOURCES = [
    ("2000", "2000/dec/sf1", "H004001", ["H004002"]),
    ("2010", "2010/dec/sf1", "H004001", ["H004002", "H004003"]),
    ("2020", "2020/dec/dhc", "H10_001N", ["H10_002N"]),
]


def _grouped_vars(table: str, groups: list) -> list[str]:
    """Full E-suffixed variable names for every code referenced by `groups`."""
    codes = {c for _, members in groups for c in members}
    return [f"{table}_{c}E" for c in sorted(codes)]


def _fetch_vars(year: int, key: str, get_vars: list[str], geo: str) -> dict:
    """Fetch ACS 5-year variables for one geography ({variable: value} dict).

    `geo` is the trailing geography clause, e.g. "for=place:12060&in=state:26".
    The API caps a single get= at 50 variables; request in chunks and merge.
    """
    record: dict = {}
    for chunk in _chunks(get_vars, 48):
        url = (
            f"https://api.census.gov/data/{year}/acs/acs5"
            f"?get={','.join(chunk)}&{geo}&key={key}"
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            rows = json.load(resp)
        record.update(dict(zip(rows[0], rows[1])))
    return record


def fetch(year: int, key: str) -> dict:
    """Fetch the ACS 5-year record for Burton city as a {variable: value} dict."""
    get_vars = [
        "NAME",
        *CORE_VARS.values(),
        *(f"B19001_{n}E" for _, codes in INCOME_GROUPS for n in codes),
        *_grouped_vars("B15003", EDU_GROUPS),
        *_grouped_vars("B08301", COMMUTE_GROUPS),
        *_grouped_vars("B01001", AGE_BANDS),
    ]
    record = _fetch_vars(year, key, get_vars, f"for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}")
    name = record.get("NAME", "")
    if not name.startswith(EXPECTED_NAME_PREFIX):
        raise SystemExit(f"Unexpected place NAME from Census: {name!r} (check FIPS codes)")
    return record


def _metrics(rec: dict) -> dict:
    """Derive the comparable headline metrics from one ACS record."""
    edu_total = _int(rec, CORE_VARS["edu_total"])
    bach = _sum(rec, "B15003", BACHELOR_CODES)
    owner = _int(rec, CORE_VARS["owner"])
    renter = _int(rec, CORE_VARS["renter"])
    age_raw = rec.get(CORE_VARS["median_age"])
    return {
        "median_income": _int(rec, CORE_VARS["median_income"]),
        "median_home_value": _int(rec, CORE_VARS["median_home_value"]),
        "owner_pct": _pct(owner, owner + renter),
        "bachelors_pct": _pct(bach, edu_total),
        "poverty_pct": _pct(_int(rec, CORE_VARS["poverty_below"]), _int(rec, CORE_VARS["poverty_total"])),
        "unemployment_pct": _pct(_int(rec, CORE_VARS["unemployed"]), _int(rec, CORE_VARS["civilian_labor_force"])),
        "median_age": round(float(age_raw), 1) if age_raw not in (None, "") else 0,
    }


def build_compare(burton: dict, year: int, key: str) -> dict | None:
    """Build the "How Burton compares" chart (Burton vs Genesee County vs Michigan).

    Returns None on any benchmark-fetch failure so the refresh still succeeds.
    """
    bench_vars = ["NAME", *CORE_VARS.values(), *(f"B15003_{c}E" for c in BACHELOR_CODES)]
    try:
        county = _fetch_vars(year, key, bench_vars, f"for=county:{COUNTY_FIPS}&in=state:{STATE_FIPS}")
        state = _fetch_vars(year, key, bench_vars, f"for=state:{STATE_FIPS}")
    except Exception as exc:  # noqa: BLE001 - benchmarks are optional
        print(f"  benchmark fetch failed ({exc}); omitting the comparison chart")
        return None

    places = [("Burton", burton), ("Genesee County", county), ("Michigan", state)]
    metrics = {name: _metrics(rec) for name, rec in places}
    rows = [
        {
            "label": label,
            "unit": unit,
            "values": [{"name": name, "value": metrics[name][mkey]} for name, _ in places],
        }
        for label, unit, mkey in COMPARE_SPECS
    ]
    return {"type": "compare", "title": f"How Burton compares ({year})", "rows": rows}


def fetch_population(dataset: str, var: str, key: str) -> int | None:
    """Fetch a single population count from a decennial dataset; None on failure."""
    url = (
        f"https://api.census.gov/data/{dataset}"
        f"?get={var}&for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}&key={key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            rows = json.load(resp)
        return int(rows[1][0])
    except Exception as exc:  # noqa: BLE001 - trend is optional; never fail the refresh
        print(f"  decennial fetch failed for {dataset} ({exc}); omitting that trend point")
        return None


def _fetch_decennial(dataset: str, get_vars: list[str], key: str) -> dict:
    """Fetch decennial variables for Burton city as a {variable: value} dict."""
    url = (
        f"https://api.census.gov/data/{dataset}"
        f"?get={','.join(get_vars)}&for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}&key={key}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        rows = json.load(resp)
    return dict(zip(rows[0], rows[1]))


def build_homeownership_trend(key: str) -> list[dict]:
    """Owner-occupied share of occupied homes across the 2000/2010/2020 censuses.

    Decennial counts only (definitions are stable across these vintages), so the
    points are directly comparable. Returns [] if fewer than two years resolve.
    """
    points = []
    for label, dataset, total_var, owner_vars in TENURE_SOURCES:
        try:
            rec = _fetch_decennial(dataset, [total_var, *owner_vars], key)
            total = int(rec[total_var])
            owner = sum(int(rec[v]) for v in owner_vars)
            if total > 0:
                points.append({"x": label, "y": round(owner / total * 100, 1)})
        except Exception as exc:  # noqa: BLE001 - one missing year shouldn't fail the refresh
            print(f"  tenure fetch failed for {label} ({exc}); omitting that point")
    return points if len(points) >= 2 else []


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _int(record: dict, key: str) -> int:
    raw = record.get(key)
    val = int(float(raw)) if raw not in (None, "") else 0
    return val if val >= 0 else 0  # Census uses large negatives for null


def _sum(record: dict, table: str, codes: list[str]) -> int:
    return sum(_int(record, f"{table}_{c}E") for c in codes)


def _pct(part: int, whole: int) -> int:
    return round(part / whole * 100) if whole else 0


def _series(record: dict, table: str, groups: list) -> list[dict]:
    return [{"label": label, "value": _sum(record, table, codes)} for label, codes in groups]


def build_panel(record: dict, year: int, trend_points: list[dict]) -> dict:
    population = _int(record, CORE_VARS["population"])
    median_age = float(record[CORE_VARS["median_age"]])
    households = _int(record, CORE_VARS["households"])
    median_income = _int(record, CORE_VARS["median_income"])
    median_home_value = _int(record, CORE_VARS["median_home_value"])
    owner = _int(record, CORE_VARS["owner"])
    renter = _int(record, CORE_VARS["renter"])
    owner_pct = _pct(owner, owner + renter)

    # Derived rates.
    edu_total = _int(record, CORE_VARS["edu_total"])
    bachelors_plus = _sum(record, "B15003", ["022", "023", "024", "025"])
    bachelors_pct = _pct(bachelors_plus, edu_total)
    unemployment_pct = _pct(_int(record, CORE_VARS["unemployed"]),
                            _int(record, CORE_VARS["civilian_labor_force"]))
    poverty_pct = _pct(_int(record, CORE_VARS["poverty_below"]),
                       _int(record, CORE_VARS["poverty_total"]))
    veterans = _int(record, CORE_VARS["veterans"])
    veterans_pct = _pct(veterans, _int(record, CORE_VARS["vet_total"]))

    income_series = [
        {"label": label, "value": _sum(record, "B19001", codes)}
        for label, codes in INCOME_GROUPS
    ]

    charts = [
        {
            "type": "donut",
            "title": "Housing tenure",
            "series": [
                {"label": "Owner-occupied", "value": owner},
                {"label": "Renter-occupied", "value": renter},
            ],
        },
        {"type": "bars", "title": "Age distribution", "series": _series(record, "B01001", AGE_BANDS)},
        {"type": "bars", "title": "Households by income", "series": income_series},
        {
            "type": "bars",
            "title": "Educational attainment (age 25+)",
            "series": _series(record, "B15003", EDU_GROUPS),
        },
        {
            "type": "donut",
            "title": "How residents get to work",
            "series": _series(record, "B08301", COMMUTE_GROUPS),
        },
    ]
    if len(trend_points) >= 2:
        charts.append({
            "type": "trend",
            "title": "Population",
            "points": trend_points,
        })

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
            {"label": "Bachelor's degree or higher", "value": f"{bachelors_pct}%", "hint": "age 25+"},
            {"label": "Unemployment rate", "value": f"{unemployment_pct}%", "hint": "civilian labor force"},
            {"label": "Below poverty line", "value": f"{poverty_pct}%"},
            {"label": "Veterans", "value": f"{veterans_pct}%", "hint": "of adults 18+"},
        ],
        "charts": charts,
        "source": f"U.S. Census Bureau, American Community Survey {year} 5-year estimates"
                  + ("; Decennial Census (2010, 2020) for the population trend" if len(trend_points) >= 2 else ""),
        "links": [
            {
                "text": "Census QuickFacts: Burton city, MI",
                "href": "https://www.census.gov/quickfacts/burtoncitymichigan",
            }
        ],
        "notes": [
            "Population trend: the 2000-2020 points are decennial census counts; the most "
            "recent figure is an ACS 5-year estimate, so it is not directly comparable to them.",
            "This product uses the Census Bureau Data API but is not endorsed or certified "
            "by the Census Bureau.",
        ],
    }


def build_trend(record: dict, year: int, key: str) -> list[dict]:
    """Population trend from decennial counts (non-overlapping) + the ACS estimate."""
    points = []
    for label, dataset, var in DECENNIAL:
        pop = fetch_population(dataset, var, key)
        if pop is not None:
            points.append({"x": label, "y": pop})
    acs_pop = _int(record, CORE_VARS["population"])
    if acs_pop:
        points.append({"x": f"{year} (est.)", "y": acs_pop})
    # Need at least two points for a meaningful trend.
    return points if len(points) >= 2 else []


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
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - report and try a fallback year
        print(f"  {args.year} ACS5 fetch failed ({exc}); retrying {args.year - 1} ...")
        record = fetch(args.year - 1, args.key)
        args.year -= 1

    trend = build_trend(record, args.year, args.key)
    panel = build_panel(record, args.year, trend)
    homeownership = build_homeownership_trend(args.key)
    if homeownership:
        panel["charts"].append({
            "type": "trend",
            "title": "Homeownership rate",
            "unit": "%",
            "points": homeownership,
        })
        panel["notes"].insert(
            len(panel["notes"]) - 1,
            "Homeownership rate is the owner-occupied share of occupied homes from the "
            "2000, 2010, and 2020 decennial censuses (directly comparable counts).",
        )
    # The wide benchmark comparison reads better at the end of the panel than in the
    # middle of the single-topic charts, so append it last.
    compare = build_compare(record, args.year, args.key)
    if compare:
        panel["charts"].append(compare)
    out = os.path.join(os.path.dirname(__file__), "..", "public", "info-demographics.json")
    out = os.path.abspath(out)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {out}")
    print(f"  population={panel['stats'][0]['value']}  median income={panel['stats'][3]['value']}")
    print(f"  charts={len(panel['charts'])}  trend points={len(trend)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
