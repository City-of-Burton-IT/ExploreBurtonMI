"""Build public/info-health.json for the Community Health dashboard.

Source: CDC PLACES (Local Data for Better Health), 2025 release -- model-based
estimates of adult (18+) prevalence from BRFSS, published at the *place* level so
Burton has its own figures (place FIPS 2612060), with Genesee County as the
benchmark (county FIPS 26049). Public domain.

These are STATISTICAL ESTIMATES of how common a condition/behaviour is among
adults, not counts of diagnosed residents -- the notes make that explicit, and
every headline figure is shown against the county so it reads as context, not a
scoreboard.

Re-runnable (committed output; the site reads the JSON, never the API):
    python tools/fetch_health.py

Stdlib only (urllib).
"""
from __future__ import annotations

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


def main() -> int:
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

    panel = {
        "title": "Community Health",
        "subtitle": f"Estimated adult health in Burton -- CDC PLACES, {RELEASE}",
        "stats": stats,
        "charts": [
            bars("Chronic conditions (estimated adult prevalence)", burton, CHART_CHRONIC),
            bars("Prevention & screening (share of adults)", burton, CHART_PREVENTION),
            bars("Lifestyle & risk factors", burton, CHART_RISK),
            bars("Health-related social needs", burton, CHART_NEEDS),
            {"type": "compare", "title": "How Burton compares to Genesee County",
             "rows": compare_rows},
        ],
        "source": (
            f"CDC PLACES: Local Data for Better Health, {RELEASE} (model-based small-area "
            "estimates from the Behavioral Risk Factor Surveillance System). Burton place "
            f"FIPS {BURTON_FIPS}; Genesee County FIPS {GENESEE_FIPS}."
        ),
        "links": [
            {"text": "CDC PLACES", "href": "https://www.cdc.gov/places/"},
            {"text": "Health & support resources (Resident Guide)", "href": "#guide/help"},
        ],
        "notes": [
            "These are model-based ESTIMATES of how common each condition or behaviour is "
            "among Burton adults -- not counts of diagnosed residents. They come from CDC's "
            "PLACES program, which projects national survey (BRFSS) results down to each "
            f"community ({RELEASE}).",
            "Every figure is shown against Genesee County so it reads as context. Small "
            "differences fall within the estimates' margin of error.",
            "Need care or help? See the Health & support resources in the Resident Guide.",
        ],
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
