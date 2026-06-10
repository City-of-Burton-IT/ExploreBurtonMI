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

Stdlib only (urllib).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

PLACE_DS = "vgc8-iyc4"   # PLACES: Place Data (GIS Friendly Format), 2025 release
COUNTY_DS = "i46a-9kgh"  # PLACES: County Data (GIS Friendly Format), 2025 release
BURTON_FIPS = "2612060"
GENESEE_FIPS = "26049"
RELEASE = "2025 release"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-health.json"))

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
ACS_TREND_CACHE = os.path.abspath(os.path.join(os.path.dirname(__file__), "health-acs-trend.json"))

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


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def fetch_row(dataset: str, field: str, value: str) -> dict:
    rows = _get(f"https://data.cdc.gov/resource/{dataset}.json?{field}={value}")
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


def _acs_uninsured_pct(year: int, key: str) -> float | None:
    """Uninsured rate (%) for Burton working-age adults (19-64) from ACS 5-year
    B27001, or None on any fetch failure (so one missing vintage never aborts)."""
    codes = sorted(set(B27001_NOCOV_19_64) | set(B27001_TOTAL_19_64))
    get_vars = ",".join(f"B27001_{c}E" for c in codes)
    url = (f"https://api.census.gov/data/{year}/acs/acs5"
           f"?get={get_vars}&for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}&key={key}")
    try:
        rows = _get(url)
    except Exception as e:
        print(f"  ACS {year}: skipped ({e})")
        return None
    rec = dict(zip(rows[0], rows[1]))

    def _sum(group: list[str]) -> int:
        return sum(int(rec.get(f"B27001_{c}E", 0) or 0) for c in group)

    total = _sum(B27001_TOTAL_19_64)
    nocov = _sum(B27001_NOCOV_19_64)
    return round(nocov / total * 100, 1) if total else None


def build_uninsured_trend(key: str | None) -> dict | None:
    """The ACS uninsured-rate trend chart, or None if unavailable.

    With a key: fetch each non-overlapping vintage and refresh the committed
    cache. Without a key: reuse the cache so a CDC-PLACES-only refresh keeps the
    trend (mirrors the --pd-cache / --trends-cache pattern elsewhere)."""
    points: list[dict] = []
    if key:
        for y in ACS_TREND_YEARS:
            pct = _acs_uninsured_pct(y, key)
            if pct is not None:
                points.append({"x": str(y), "y": pct})
        if points:
            with open(ACS_TREND_CACHE, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(points, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
    elif os.path.exists(ACS_TREND_CACHE):
        print("  ACS key absent -> reusing committed uninsured-trend cache")
        with open(ACS_TREND_CACHE, encoding="utf-8") as fh:
            points = json.load(fh)
    else:
        print("  ACS key absent and no cache -> uninsured trend SKIPPED "
              "(set CENSUS_API_KEY to build it)")
        return None
    if not points:
        return None
    return {
        "type": "trend",
        "title": "Uninsured rate, working-age adults (19-64), by year",
        "unit": "%",
        "points": points,
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

    compare_rows = []
    for code in COMPARE:
        b, g = prev(burton, code), prev(genesee, code)
        if b is not None and g is not None:
            compare_rows.append({
                "label": LABELS[code],
                "unit": "%",
                "values": [
                    {"name": "Burton", "value": b},
                    {"name": "Genesee County", "value": g},
                ],
            })

    # Optional ACS uninsured-rate trend (leads the panel as the "health over time"
    # line). Built from a DIFFERENT source than the CDC PLACES estimates below.
    uninsured_trend = build_uninsured_trend(args.key)

    charts = [
        bars("Chronic conditions (estimated adult prevalence)", burton, CHART_CHRONIC),
        bars("Prevention & screening (share of adults)", burton, CHART_PREVENTION),
        bars("Lifestyle & risk factors", burton, CHART_RISK),
        bars("Health-related social needs", burton, CHART_NEEDS),
        {"type": "compare", "title": "How Burton compares to Genesee County",
         "rows": compare_rows},
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
        "Every figure is shown against Genesee County so it reads as context. Small "
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

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  stats: {len(stats)}  charts: {len(panel['charts'])}  compare rows: {len(compare_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
