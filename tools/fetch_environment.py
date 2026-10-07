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

Uses the shared tools/lib helpers (HTTP retry, atomic writes).
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import zipfile

from lib.httpio import get_bytes
from lib.iox import write_json
from lib.paths import public_path

STATE = "Michigan"
COUNTY = "Genesee"
YEARS = list(range(2015, 2026))  # 2025 may not exist yet -> skipped gracefully
BASE = "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_{}.zip"
OUT = public_path("info-environment.json")
NFIP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nfip-burton.json")
HIGH_ZONE = "High risk (A and V zones)"


def fetch_year(year: int) -> dict | None:
    url = BASE.format(year)
    try:
        # attempts=2: the newest year usually 404s until EPA publishes it, so
        # keep the missing-year probe cheap while still absorbing one hiccup.
        blob = get_bytes(url, attempts=2, timeout=60)
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


def load_nfip(path: str = NFIP_FILE) -> dict | None:
    """Read the committed NFIP aggregates; None if absent, sys.exit on shape errors."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    where = "nfip-burton.json"
    pif = d.get("policies_in_force")
    if not isinstance(pif, dict) or not all(isinstance(pif.get(k), (int, float)) for k in ("count", "median_premium")):
        sys.exit(f"{where}: policies_in_force needs numeric count and median_premium")
    zones = d.get("policies_in_force_by_zone")
    if not isinstance(zones, list) or not all(
        isinstance(z, dict) and isinstance(z.get("count"), int) and z.get("zone_group") for z in zones
    ):
        sys.exit(f"{where}: policies_in_force_by_zone must list zone_group/count rows")
    ct = d.get("claims_total")
    if not isinstance(ct, dict) or not isinstance(ct.get("count"), int) or not isinstance(ct.get("paid"), (int, float)):
        sys.exit(f"{where}: claims_total needs integer count and numeric paid")
    dec = d.get("claims_by_decade")
    if not isinstance(dec, list) or len(dec) < 3 or not all(
        isinstance(r, dict) and r.get("decade") and isinstance(r.get("count"), int) for r in dec
    ):
        sys.exit(f"{where}: claims_by_decade needs at least three decade/count rows")
    if not isinstance(d.get("as_of"), str) or not d["as_of"]:
        sys.exit(f"{where}: as_of must be a non-empty string")
    return d


def add_flood(panel: dict, nfip: dict) -> None:
    """Append NFIP flood-insurance stats, charts, notes, source and link to the panel."""
    pif, ct = nfip["policies_in_force"], nfip["claims_total"]
    zones = {z["zone_group"]: z["count"] for z in nfip["policies_in_force_by_zone"]}
    n = pif["count"]
    high = zones.get(HIGH_ZONE, 0)
    share = round(high / n * 100) if n else 0
    as_of = nfip["as_of"]
    panel["stats"] += [
        {"label": "Flood insurance policies in force", "value": f"{n:,}", "hint": f"FEMA NFIP, as of {as_of}"},
        {"label": "Homes in high-risk zones with a policy", "value": f"{high:,}", "hint": f"{share}% of policies in force"},
        {"label": "Flood claims paid since 1978", "value": f"{ct['count']:,}", "hint": f"${ct['paid']:,.0f} paid in total"},
        {"label": "Typical annual premium", "value": f"${pif['median_premium']:,.0f}", "hint": "median of policies in force"},
    ]
    panel["charts"] += [
        {"type": "bars", "title": "Flood insurance claims by decade", "unit": "",
         "series": [{"label": r["decade"], "value": r["count"]} for r in nfip["claims_by_decade"]]},
        {"type": "donut", "title": "Where flood policies sit", "unit": "",
         "series": [{"label": z["zone_group"], "value": z["count"]} for z in nfip["policies_in_force_by_zone"]]},
    ]
    panel["notes"] += [
        "National Flood Insurance Program (NFIP) figures cover only properties with a federal flood "
        "policy, so these counts are not the number of homes at risk. The map's Flood zones (FEMA) "
        "overlay shows the mapped zones.",
        "Flood claims are historical payments on record; amounts are not adjusted for inflation.",
    ]
    panel["source"] += (
        f" Flood insurance: FEMA OpenFEMA NFIP Policies and Claims v3 for the City of Burton, "
        f"aggregates only, as of {as_of}."
    )
    panel["links"].append({"text": "FEMA Flood Map Service Center", "href": "https://msc.fema.gov/portal/home"})


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

    nfip = load_nfip()
    if nfip:
        add_flood(panel, nfip)
        print(f"  flood insurance: {nfip['policies_in_force']['count']} policies in force, "
              f"{nfip['claims_total']['count']} claims (as of {nfip['as_of']})")
    else:
        print("  flood insurance: tools/data/nfip-burton.json absent, skipped")

    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  years: {len(rows)} ({min(rows)}-{max(rows)})  stats: {len(panel['stats'])}  charts: {len(panel['charts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
