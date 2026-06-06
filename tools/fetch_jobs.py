"""Build public/info-jobs.json for the Jobs & Employers dashboard.

County-level (Genesee County, 26049) -- the federal business/labor series are not
published at city level, so everything here is labelled "Genesee County". Burton
is part of that county.

Sources (public domain):
  * U.S. Census County Business Patterns (CBP), 2022 -- establishments, paid
    employment, and annual payroll by industry (NAICS sector). Needs a free Census
    API key (env CENSUS_API_KEY or --key), same as fetch_census.py.
  * U.S. Bureau of Labor Statistics, Local Area Unemployment Statistics (LAUS) --
    the county unemployment rate (latest month + a multi-year annual-average
    trend). No key required.

Re-runnable (committed output; the site reads the JSON, never the API):
    set CENSUS_API_KEY=...   &&   python tools/fetch_jobs.py

Stdlib only (urllib).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

CBP_YEAR = 2022
STATE_FIPS = "26"
COUNTY_FIPS = "049"
LAUS_SERIES = "LAUCN260490000000003"  # Genesee County, MI -- unemployment rate
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-jobs.json"))

# Short display labels for the NAICS sector codes CBP returns.
SECTOR_LABELS = {
    "11": "Agriculture", "21": "Mining", "22": "Utilities", "23": "Construction",
    "31-33": "Manufacturing", "42": "Wholesale trade", "44-45": "Retail trade",
    "48-49": "Transportation & warehousing", "51": "Information",
    "52": "Finance & insurance", "53": "Real estate", "54": "Professional & technical",
    "55": "Company management", "56": "Administrative & waste services",
    "61": "Educational services", "62": "Health care & social assistance",
    "71": "Arts, entertainment & recreation", "72": "Accommodation & food service",
    "81": "Other services",
}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def _post_json(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def fetch_cbp(key: str) -> tuple[dict, list]:
    """Return (totals, sectors). totals = {estab,emp,payann}; sectors = list of
    {code,label,estab,emp,payann}."""
    url = (
        f"https://api.census.gov/data/{CBP_YEAR}/cbp"
        f"?get=NAICS2017_LABEL,ESTAB,EMP,PAYANN&for=county:{COUNTY_FIPS}"
        f"&in=state:{STATE_FIPS}&NAICS2017=*&key={key}"
    )
    rows = _get_json(url)
    hdr = rows[0]
    ci = {name: i for i, name in enumerate(hdr)}
    totals: dict = {}
    sectors = []
    for r in rows[1:]:
        code = r[ci["NAICS2017"]]
        try:
            estab, emp, payann = int(r[ci["ESTAB"]]), int(r[ci["EMP"]]), int(r[ci["PAYANN"]])
        except (ValueError, TypeError):
            continue
        if code == "00":
            totals = {"estab": estab, "emp": emp, "payann": payann}
        elif code in SECTOR_LABELS and emp > 0:
            sectors.append({"code": code, "label": SECTOR_LABELS[code],
                            "estab": estab, "emp": emp, "payann": payann})
    return totals, sectors


def fetch_unemployment() -> tuple[dict | None, list]:
    """Return (latest_month, annual_trend). latest_month = {value,label}; trend =
    [{x:year, y:rate}] of annual averages."""
    res = _post_json(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        {"seriesid": [LAUS_SERIES], "startyear": str(CBP_YEAR - 6),
         "endyear": "2026", "annualaverage": True},
    )
    data = res.get("Results", {}).get("series", [{}])[0].get("data", [])
    # Annual averages (period M13), oldest -> newest.
    annual = sorted(
        ({"x": d["year"], "y": float(d["value"])} for d in data if d["period"] == "M13"),
        key=lambda p: p["x"],
    )
    # Latest actual month (skip M13) -- the data is returned newest-first.
    latest = None
    for d in data:
        if d["period"] != "M13":
            latest = {"value": float(d["value"]), "label": f"{d['periodName']} {d['year']}"}
            break
    return latest, annual


def _fmt_big(dollars: int) -> str:
    if dollars >= 1_000_000_000:
        return f"${dollars / 1e9:.2f}B"
    if dollars >= 1_000_000:
        return f"${dollars / 1e6:.0f}M"
    return f"${dollars:,}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Genesee County jobs/employer data.")
    parser.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"),
                        help="Census API key (or set CENSUS_API_KEY)")
    args = parser.parse_args()
    if not args.key:
        print("ERROR: a Census API key is required (set CENSUS_API_KEY or pass --key).")
        return 2

    totals, sectors = fetch_cbp(args.key)
    latest_unemp, unemp_trend = fetch_unemployment()
    if not totals:
        print("ERROR: no CBP totals returned.")
        return 1

    payroll = totals["payann"] * 1000  # CBP payroll is in $1,000s
    avg_wage = payroll / totals["emp"] if totals["emp"] else 0

    stats = [
        {"label": "Establishments", "value": f"{totals['estab']:,}", "hint": f"Genesee County, {CBP_YEAR}"},
        {"label": "Paid employees", "value": f"{totals['emp']:,}", "hint": f"Genesee County, {CBP_YEAR}"},
        {"label": "Annual payroll", "value": _fmt_big(payroll), "hint": f"Genesee County, {CBP_YEAR}"},
        {"label": "Average annual wage", "value": f"${avg_wage / 1000:.1f}K", "hint": f"payroll / employees, {CBP_YEAR}"},
    ]
    if latest_unemp:
        stats.append({"label": "Unemployment rate", "value": f"{latest_unemp['value']}%",
                      "hint": f"Genesee County, {latest_unemp['label']}"})

    by_jobs = sorted(sectors, key=lambda s: -s["emp"])[:10]
    jobs_chart = {
        "type": "bars", "title": f"Jobs by industry (Genesee County, {CBP_YEAR})", "unit": "",
        "series": [{"label": s["label"], "value": s["emp"]} for s in by_jobs],
    }
    # Average wage by industry, restricted to the larger sectors so a tiny,
    # high-wage outlier doesn't dominate; sorted high -> low.
    wage_sectors = [s for s in sectors if s["emp"] >= 1000]
    by_wage = sorted(wage_sectors, key=lambda s: -(s["payann"] * 1000 / s["emp"]))[:10]
    wage_chart = {
        "type": "bars", "title": "Average annual wage by industry", "unit": "$",
        "series": [{"label": s["label"], "value": round(s["payann"] * 1000 / s["emp"])} for s in by_wage],
    }
    charts = [jobs_chart, wage_chart]
    if len(unemp_trend) >= 2:
        charts.append({"type": "trend", "title": "Unemployment rate (Genesee County, annual avg)",
                       "unit": "%", "points": unemp_trend})

    panel = {
        "title": "Jobs & Employers",
        "subtitle": f"Genesee County employment -- Census County Business Patterns {CBP_YEAR} + BLS",
        "stats": stats,
        "charts": charts,
        "source": (
            f"U.S. Census County Business Patterns {CBP_YEAR} (establishments, employment, payroll "
            "by NAICS sector) and U.S. Bureau of Labor Statistics Local Area Unemployment Statistics "
            "(county unemployment rate). Genesee County, MI (FIPS 26049)."
        ),
        "links": [
            {"text": "Census County Business Patterns", "href": "https://www.census.gov/programs-surveys/cbp.html"},
            {"text": "BLS Local Area Unemployment", "href": "https://www.bls.gov/lau/"},
        ],
        "notes": [
            "These figures are for all of Genesee County, not Burton alone -- the federal "
            "business and labor series are not published at the city level. Burton is one of "
            "the county's communities.",
            "Establishment, employment, and payroll counts exclude most government, agricultural, "
            "and self-employed workers (a County Business Patterns convention).",
        ],
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  stats: {len(stats)}  charts: {len(charts)}  sectors: {len(sectors)}  "
          f"unemp trend yrs: {len(unemp_trend)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
