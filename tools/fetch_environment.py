"""Build public/info-environment.json for the Environment dashboard.

Centered on AIR QUALITY, which is the piece that's cleanly published, multi-year,
and redistributable: EPA AirData "Annual AQI by County" files (public domain), for
Genesee County, MI. Each year's file is a small zip of one CSV covering every U.S.
county; we pull the Genesee row.

Drinking water, live/real-time AQI, and environmental-justice screening are LINKED
OUT rather than baked in (they're either volatile or not cleanly fetchable), per
the project's publish-vs-link rule.

County-level (Genesee), air monitors aren't sited per-city. Burton is in the county.

Re-runnable (committed output; the site reads the JSON, never the network):
    python tools/fetch_environment.py

Stdlib only (urllib, zipfile, csv).
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.request
import zipfile

STATE = "Michigan"
COUNTY = "Genesee"
YEARS = list(range(2015, 2026))  # 2025 may not exist yet -> skipped gracefully
BASE = "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_{}.zip"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-environment.json"))


def fetch_year(year: int) -> dict | None:
    url = BASE.format(year)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            blob = resp.read()
    except Exception as e:
        print(f"  {year}: skipped ({e})")
        return None
    zf = zipfile.ZipFile(io.BytesIO(blob))
    name = zf.namelist()[0]
    text = zf.read(name).decode("utf-8", errors="replace")
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("State") == STATE and row.get("County") == COUNTY:
            return {k: row[k] for k in row}
    return None


def _i(row: dict, key: str) -> int:
    try:
        return int(row.get(key, 0) or 0)
    except ValueError:
        return 0


def main() -> int:
    rows: dict[int, dict] = {}
    print("Fetching EPA AirData annual AQI (Genesee County):")
    for y in YEARS:
        r = fetch_year(y)
        if r:
            rows[y] = r
            print(f"  {y}: median AQI {r.get('Median AQI')}, good {r.get('Good Days')}/{r.get('Days with AQI')}")
    if not rows:
        print("ERROR: no AQI data fetched.")
        return 1

    latest_year = max(rows)
    L = rows[latest_year]
    total = _i(L, "Days with AQI")
    good = _i(L, "Good Days")
    moderate = _i(L, "Moderate Days")
    usg = _i(L, "Unhealthy for Sensitive Groups Days")
    unhealthy_plus = usg + _i(L, "Unhealthy Days") + _i(L, "Very Unhealthy Days") + _i(L, "Hazardous Days")
    good_pct = round(good / total * 100) if total else 0

    stats = [
        {"label": "Good air-quality days", "value": f"{good_pct}%", "hint": f"{good} of {total} days, {latest_year}"},
        {"label": "Median AQI", "value": str(_i(L, "Median AQI")), "hint": f"{latest_year} (0-50 = good)"},
        {"label": "Moderate days", "value": str(moderate), "hint": f"{latest_year}"},
        {"label": "Unhealthy days", "value": str(unhealthy_plus), "hint": f"any sensitive+ level, {latest_year}"},
    ]

    # Trend: median AQI by year (lower is better).
    median_trend = [{"x": str(y), "y": _i(rows[y], "Median AQI")} for y in sorted(rows)]

    # Trend: % of days rated GOOD, by year (higher is better). The same Good Days /
    # Days with AQI fields as the headline stat, but as a multi-year series -- a more
    # intuitive "is our air getting better?" view for residents than median AQI.
    def _good_pct_for(r: dict) -> int:
        t = _i(r, "Days with AQI")
        return round(_i(r, "Good Days") / t * 100) if t else 0

    good_trend = [{"x": str(y), "y": _good_pct_for(rows[y])} for y in sorted(rows)]

    # Latest-year distribution of days by AQI category.
    days_chart = {
        "type": "bars", "title": f"Air-quality days by level ({latest_year})", "unit": "",
        "series": [
            {"label": "Good", "value": good},
            {"label": "Moderate", "value": moderate},
            {"label": "Unhealthy for sensitive groups", "value": usg},
            {"label": "Unhealthy or worse", "value": _i(L, "Unhealthy Days") + _i(L, "Very Unhealthy Days") + _i(L, "Hazardous Days")},
        ],
    }
    # Which pollutant set the daily AQI most often (latest year).
    pollutants = [
        ("Ozone", _i(L, "Days Ozone")),
        ("Fine particles (PM2.5)", _i(L, "Days PM2.5")),
        ("Coarse particles (PM10)", _i(L, "Days PM10")),
        ("Nitrogen dioxide", _i(L, "Days NO2")),
        ("Carbon monoxide", _i(L, "Days CO")),
    ]
    pollutant_chart = {
        "type": "bars", "title": f"Days set by each pollutant ({latest_year})", "unit": "",
        "series": [{"label": n, "value": v} for n, v in pollutants if v > 0],
    }

    charts = [
        {"type": "trend", "title": "Good air-quality days by year (higher is better)", "unit": "%", "points": good_trend},
        {"type": "trend", "title": "Median AQI by year (lower is better)", "unit": "", "points": median_trend},
        days_chart,
        pollutant_chart,
    ]

    panel = {
        "title": "Environment",
        "subtitle": f"Air quality in Genesee County: EPA AirData, through {latest_year}",
        "stats": stats,
        "charts": charts,
        "source": (
            "U.S. EPA AirData, Annual Air Quality Index (AQI) by County, for Genesee County, MI. "
            "The AQI summarizes ground-level ozone and particle pollution into a 0-500 scale "
            "(0-50 good, 51-100 moderate, 101-150 unhealthy for sensitive groups)."
        ),
        "links": [
            {"text": "Live air quality (AirNow)", "href": "https://www.airnow.gov/?city=Burton&state=MI&country=USA"},
            {"text": "Burton drinking-water quality report (EPA)", "href": "https://ofmpub.epa.gov/apex/safewater/f?p=136:102"},
            {"text": "EPA EJScreen (environmental justice)", "href": "https://www.epa.gov/ejscreen"},
            {"text": "Michigan EGLE (environment)", "href": "https://www.michigan.gov/egle"},
        ],
        "notes": [
            "Air-quality figures are for Genesee County (air monitors are not sited per city); "
            "Burton is within the county.",
            "The AQI is a daily 0-500 index: 0-50 good, 51-100 moderate, 101-150 unhealthy for "
            "sensitive groups. 'Days set by each pollutant' shows what drove the daily index most "
            "often, usually fine particles (PM2.5) or ozone.",
            "Drinking water, live air readings, and environmental-justice screening are linked "
            "above (live or detailed data lives better at the source than in a yearly snapshot).",
        ],
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  years: {len(rows)} ({min(rows)}-{max(rows)})  stats: {len(stats)}  charts: {len(charts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
