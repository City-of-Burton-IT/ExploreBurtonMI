"""Build public/info-health.json for the Community Health dashboard.

Source: CDC PLACES (Local Data for Better Health), 2025 release: model-based
estimates of adult (18+) prevalence from BRFSS, published at the *place* level so
Burton has its own figures (place FIPS 2612060), with Genesee County as the
benchmark (county FIPS 26049). Public domain.

These are STATISTICAL ESTIMATES of how common a condition/behaviour is among
adults, not counts of diagnosed residents: the notes make that explicit, and
every headline figure is shown against the county so it reads as context, not a
scoreboard.

Re-runnable (committed output; the site reads the JSON, never the API):
    python tools/fetch_health.py

Uses the shared tools/lib helpers (HTTP retry, atomic writes).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

PLACE_DS = "vgc8-iyc4"   # PLACES: Place Data (GIS Friendly Format), 2025 release
COUNTY_DS = "i46a-9kgh"  # PLACES: County Data (GIS Friendly Format), 2025 release
BURTON_FIPS = "2612060"
GENESEE_FIPS = "26049"
RELEASE = "2025 release"
OUT = public_path("info-health.json")

# --- ACS uninsured-rate trend (a multi-year "health over time" line) ----------
# Distinct from the CDC PLACES single-snapshot estimates above: the U.S. Census
# ACS 5-year detailed table B27001 (Health Insurance Coverage Status by Sex by
# Age). ACS 5-year vintages OVERLAP and must not be charted year over year, so we
# use NON-OVERLAPPING windows (2009-13, 2014-18, 2019-23) -- the Census-recommended
# spacing, the same rule the demographics trends use (see fetch_census.py).
# Requires CENSUS_API_KEY (or --key); the trend is cached so a keyless CDC-only
# refresh preserves it.
PLACE_FIPS = "12060"
STATE_FIPS = "26"
ACS_TREND_YEARS = [2013, 2018, 2023]
# B27001 codes verified against the 2023 group JSON. The five working-age bands
# per sex are 19-25, 26-34, 35-44, 45-54, 55-64 (= ages 19-64; there is no clean
# 18 split). "No health insurance coverage" cells (numerator) and band totals
# (denominator):
B27001_NOCOV_19_64 = ["011", "014", "017", "020", "023",   # male, no coverage
                      "039", "042", "045", "048", "051"]   # female, no coverage
B27001_TOTAL_19_64 = ["009", "012", "015", "018", "021",   # male, band totals
                      "037", "040", "043", "046", "049"]   # female, band totals
ACS_TREND_CACHE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".cache", "health-acs-trend.json")
)

# measure code -> human label (subset of the 40 PLACES measures we surface)
LABELS = {
    "access2": "Without health insurance (18-64)",
    "checkup": "Routine checkup, past year",
    "bphigh": "High blood pressure",
    "highchol": "High cholesterol",
    "obesity": "Obesity",
    "arthritis": "Arthritis",
    "depression": "Depression",
    "diabetes": "Diabetes",
    "casthma": "Current asthma",
    "copd": "COPD",
    "chd": "Heart disease",
    "cholscreen": "Cholesterol screening",
    "mammouse": "Mammogram (women 50-74)",
    "colon_screen": "Colon cancer screening",
    "dental": "Dental visit, past year",
    "csmoking": "Currently smoke",
    "lpa": "No leisure-time exercise",
    "sleep": "Short sleep (under 7 hrs)",
    "binge": "Binge drinking",
    "foodinsecu": "Food insecurity",
    "housinsecu": "Housing insecurity",
    "lacktrpt": "Lack of transportation",
    "shututility": "Utility shut-off risk",
    "isolation": "Social isolation",
}

# headline stat cards (code, hint)
STATS = [
    ("access2", "adults 18-64"),
    ("checkup", "adults"),
    ("bphigh", "adults"),
    ("diabetes", "adults"),
    ("csmoking", "adults"),
    ("obesity", "adults"),
]

CHART_CHRONIC = ["bphigh", "highchol", "obesity", "arthritis", "depression",
                 "diabetes", "casthma", "copd", "chd"]
CHART_PREVENTION = ["cholscreen", "checkup", "mammouse", "colon_screen", "dental"]
CHART_RISK = ["sleep", "lpa", "csmoking", "binge"]
CHART_NEEDS = ["isolation", "foodinsecu", "housinsecu", "shututility", "lacktrpt"]
COMPARE = ["access2", "csmoking", "obesity", "diabetes", "bphigh"]

# All 11 incorporated cities in Genesee County, for the "Genesee County cities"
# view on the compare chart (the #28 toggle, framed collaboratively for health).
# Place FIPS (full GEOID) verified present in CDC PLACES, 2026-06-10.
GENESEE_CITY_FIPS = {
    "Burton": "2612060", "Clio": "2616620", "Davison": "2619880",
    "Fenton": "2627760", "Flint": "2629000", "Flushing": "2629200",
    "Grand Blanc": "2633280", "Linden": "2647820", "Montrose": "2655280",
    "Mount Morris": "2655960", "Swartz Creek": "2677700",
}

# Collaborative framing for the cities view: a regional picture for working
# together, NOT a "who's worst" ranking (health burden is sensitive).
CITIES_LEDE = (
    "Health challenges don't stop at city limits. Seeing how Genesee County "
    "communities compare helps the county, Burton, and its neighbors focus "
    "resources and tackle these together. Burton is highlighted; these are "
    "model-based estimates, so small differences aren't meaningful."
)


def fetch_row(dataset: str, field: str, value: str) -> dict:
    rows = get_json(f"https://data.cdc.gov/resource/{dataset}.json?{field}={value}", timeout=40)
    if not rows:
        raise SystemExit(f"No PLACES row for {field}={value} in {dataset}")
    return rows[0]


def prev(row: dict, code: str):
    raw = row.get(f"{code}_crudeprev")
    return round(float(raw), 1) if raw not in (None, "") else None


def bars(title: str, row: dict, codes: list) -> dict:
    series = [{"label": LABELS[c], "value": v}
              for c in codes if (v := prev(row, c)) is not None]
    series.sort(key=lambda s: -s["value"])
    return {"type": "bars", "title": title, "unit": "%", "series": series}


def fetch_genesee_cities() -> dict:
    """CDC PLACES place rows for the 11 Genesee County cities, keyed by name.

    One keyless Socrata query (placefips IN ...). A city absent from the result
    is simply skipped; the ranking tolerates fewer than 11."""
    ids = "','".join(GENESEE_CITY_FIPS.values())
    where = urllib.parse.quote(f"placefips in ('{ids}')", safe="")
    url = f"https://data.cdc.gov/resource/{PLACE_DS}.json?$where={where}&$limit=50"
    by_fips = {r.get("placefips"): r for r in get_json(url, timeout=40)}
    return {name: by_fips[fips] for name, fips in GENESEE_CITY_FIPS.items() if fips in by_fips}


def build_city_rankings(city_rows: dict) -> dict:
    """For each COMPARE measure, a high-to-low ranked list of {name, value} across
    the cities (Burton included). Cities missing a measure drop out of its list."""
    rankings: dict = {}
    for code in COMPARE:
        vals = [{"name": n, "value": v}
                for n, row in city_rows.items() if (v := prev(row, code)) is not None]
        vals.sort(key=lambda d: d["value"], reverse=True)
        rankings[code] = vals
    return rankings


# The two series shown on the uninsured trend (Burton vs the state), each a
# trailing ACS geography clause.
ACS_GEOS = [
    ("Burton", f"for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}"),
    ("Michigan", f"for=state:{STATE_FIPS}"),
]


def _acs_uninsured_pct(year: int, key: str, geo: str) -> float | None:
    """Working-age (19-64) uninsured rate (%) for one geography from ACS 5-year
    B27001, or None on any fetch failure (so one missing vintage never aborts)."""
    codes = sorted(set(B27001_NOCOV_19_64) | set(B27001_TOTAL_19_64))
    get_vars = ",".join(f"B27001_{c}E" for c in codes)
    url = f"https://api.census.gov/data/{year}/acs/acs5?get={get_vars}&{geo}&key={key}"
    try:
        rows = get_json(url, timeout=40)
    except Exception as e:
        print(f"  ACS {year} ({geo}): skipped ({e})")
        return None
    rec = dict(zip(rows[0], rows[1]))

    def _sum(group: list[str]) -> int:
        return sum(int(rec.get(f"B27001_{c}E", 0) or 0) for c in group)

    total = _sum(B27001_TOTAL_19_64)
    nocov = _sum(B27001_NOCOV_19_64)
    return round(nocov / total * 100, 1) if total else None


def build_uninsured_trend(key: str | None) -> dict | None:
    """Burton-vs-Michigan working-age (19-64) uninsured-rate trend (two lines),
    or None if unavailable. Both series use the identical B27001 method and
    non-overlapping vintages so they are directly comparable.

    With a key: fetch each series + vintage and refresh the committed cache.
    Without a key: reuse the cache so a CDC-PLACES-only refresh keeps the trend."""
    lines: list[dict] = []
    if key:
        for name, geo in ACS_GEOS:
            pts = [{"x": str(y), "y": p}
                   for y in ACS_TREND_YEARS if (p := _acs_uninsured_pct(y, key, geo)) is not None]
            if pts:
                lines.append({"label": name, "points": pts})
        if lines:
            os.makedirs(os.path.dirname(ACS_TREND_CACHE), exist_ok=True)
            write_json(ACS_TREND_CACHE, lines)
    elif os.path.exists(ACS_TREND_CACHE):
        print("  ACS key absent -> reusing committed uninsured-trend cache")
        with open(ACS_TREND_CACHE, encoding="utf-8") as fh:
            lines = json.load(fh)
    else:
        print("  ACS key absent and no cache -> uninsured trend SKIPPED "
              "(set CENSUS_API_KEY to build it)")
        return None
    if not lines:
        return None
    return {
        "type": "trend",
        "title": "Uninsured rate, working-age adults (19-64): Burton vs Michigan, by year",
        "unit": "%",
        "lines": lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Community Health dashboard JSON.")
    ap.add_argument(
        "--key", default=os.environ.get("CENSUS_API_KEY"),
        help="Census API key for the ACS uninsured-rate trend (or set CENSUS_API_KEY). "
             "Optional: without it the CDC PLACES panel still builds and the committed "
             "trend cache is reused.",
    )
    args = ap.parse_args()

    burton = fetch_row(PLACE_DS, "placefips", BURTON_FIPS)
    genesee = fetch_row(COUNTY_DS, "countyfips", GENESEE_FIPS)
    pop = burton.get("totalpopulation")

    stats = []
    for code, hint in STATS:
        v = prev(burton, code)
        if v is not None:
            stats.append({"label": LABELS[code], "value": f"{v}%", "hint": hint})

    # Genesee County cities ranking for the compare toggle (collaborative framing).
    try:
        city_rankings = build_city_rankings(fetch_genesee_cities())
    except Exception as exc:  # noqa: BLE001 - the cities view is optional
        print(f"  Genesee cities fetch failed ({exc}); cities view omitted")
        city_rankings = {}

    compare_rows = []
    for code in COMPARE:
        b, g = prev(burton, code), prev(genesee, code)
        if b is not None and g is not None:
            row = {
                "label": LABELS[code],
                "unit": "%",
                "values": [
                    {"name": "Burton", "value": b},
                    {"name": "Genesee County", "value": g},
                ],
            }
            ranked = city_rankings.get(code, [])
            if len(ranked) >= 3:
                row["cities"] = ranked
            compare_rows.append(row)

    # Optional ACS uninsured-rate trend (leads the panel as the "health over time"
    # line). Built from a DIFFERENT source than the CDC PLACES estimates below.
    uninsured_trend = build_uninsured_trend(args.key)

    compare_chart = {
        "type": "compare",
        "title": "How Burton compares to Genesee County",
        "rows": compare_rows,
    }
    # When the cities ranking is present, frame that view collaboratively.
    if any(r.get("cities") for r in compare_rows):
        compare_chart["citiesLede"] = CITIES_LEDE

    charts = [
        bars("Chronic conditions (estimated adult prevalence)", burton, CHART_CHRONIC),
        bars("Prevention & screening (share of adults)", burton, CHART_PREVENTION),
        bars("Lifestyle & risk factors", burton, CHART_RISK),
        bars("Health-related social needs", burton, CHART_NEEDS),
        compare_chart,
    ]
    if uninsured_trend:
        charts.insert(0, uninsured_trend)

    source = (
        f"CDC PLACES: Local Data for Better Health, {RELEASE} (model-based small-area "
        "estimates from the Behavioral Risk Factor Surveillance System). Burton place "
        f"FIPS {BURTON_FIPS}; Genesee County FIPS {GENESEE_FIPS}."
    )
    if uninsured_trend:
        source += (
            " The 'Uninsured rate ... by year' line is a separate source: U.S. Census ACS "
            "5-year, table B27001 (working-age adults 19-64), non-overlapping vintages."
        )

    notes = [
        "These are model-based ESTIMATES of how common each condition or behaviour is "
        "among Burton adults, not counts of diagnosed residents. They come from CDC's "
        "PLACES program, which projects national survey (BRFSS) results down to each "
        f"community ({RELEASE}).",
        "Every figure is shown against Genesee County (and, in the cities view, "
        "alongside other county communities) so it reads as context. Small "
        "differences fall within the estimates' margin of error.",
        "Need care or help? See the Health & support resources in the Resident Guide.",
    ]
    if uninsured_trend:
        notes.insert(1, (
            "The 'Uninsured rate, working-age adults (19-64), by year' line is from the "
            "U.S. Census ACS (5-year survey) -- a different source and method than the CDC "
            "PLACES estimates, shown at non-overlapping years so the points are comparable. "
            "It is not the same series as the PLACES 'Without health insurance (18-64)' figure."
        ))

    panel = {
        "title": "Community Health",
        "subtitle": f"Estimated adult health in Burton: CDC PLACES, {RELEASE}",
        "stats": stats,
        "charts": charts,
        "source": source,
        "links": [
            {"text": "CDC PLACES", "href": "https://www.cdc.gov/places/"},
            {"text": "Health & support resources (Resident Guide)", "href": "#guide/help"},
        ],
        "notes": notes,
    }
    if pop:
        panel["notes"].insert(0, f"Estimates cover Burton's adult population (city total ~{int(pop):,}).")

    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  stats: {len(stats)}  charts: {len(panel['charts'])}  compare rows: {len(compare_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
