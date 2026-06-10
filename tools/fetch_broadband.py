# Build public/info-broadband.json for the Broadband Access dashboard.
#
# Source: FCC National Broadband Map / Broadband Data Collection (BDC), the
# "Summary by Geography Type - Census Place" fixed-broadband file for Michigan
# (state 26), filtered to Burton (GEOID 2612060). Public data.
#
# The FCC API needs a free account: a username (registration email) AND an API
# token, sent together as request headers. Pass --user/--token or set
# FCC_USERNAME / FCC_HASH. Credentials are runtime-only and NEVER committed.
#   python tools/fetch_broadband.py --user you@example.gov --token <hash>
#
# Re-runnable (committed output; the site reads the JSON, never the FCC API).
# Stdlib only (urllib/zipfile/csv).
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile

API = "https://broadbandmap.fcc.gov/api/public/map"
STATE_FIPS = "26"          # Michigan
BURTON_GEOID = "2612060"   # Burton city
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-broadband.json"))

SPEED_TIERS = [
    ("speed_25_3", "25 / 3 Mbps"),
    ("speed_100_20", "100 / 20 Mbps"),
    ("speed_250_25", "250 / 25 Mbps"),
    ("speed_1000_100", "Gigabit (1000 / 100)"),
]

# Satellite-only holding companies cover ~everyone, so they're listed separately
# from the terrestrial providers residents actually choose between.
SATELLITE_HINTS = ("echostar", "hughes", "viasat", "space exploration", "starlink")
# Friendlier brand names for the well-known holding companies.
BRANDS = {
    "Comcast Corporation": "Comcast (Xfinity)",
    "Charter Communications": "Charter (Spectrum)",
    "AT&T Inc.": "AT&T",
    "Verizon Communications Inc.": "Verizon",
    "T-Mobile USA, Inc.": "T-Mobile Home Internet",
    "EchoStar Corporation": "HughesNet (EchoStar)",
    "Space Exploration Technologies Corp.": "Starlink (SpaceX)",
    "Viasat, Inc.": "Viasat",
    "Bitwise Inc.": "Bitwise",
}


def _get(url: str, headers: dict, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _download_rows(H: dict, file_meta: dict) -> list:
    raw = _get(f"{API}/downloads/downloadFile/availability/{file_meta['file_id']}", H, 240)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    except zipfile.BadZipFile:
        text = raw.decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(text)))


def build_providers(files: list, H: dict) -> list:
    """Burton's fixed-broadband providers with residential coverage %, named and
    flagged satellite. From the FCC public Provider Summary + Provider List files."""
    ps = next((f for f in files
               if f.get("subcategory") == "Provider Summary by Geography Type"
               and (f.get("file_type") or "").lower() == "csv"), None)
    pl = next((f for f in files
               if "provider" in (f.get("subcategory") or "").lower()
               and "list" in (f.get("subcategory") or "").lower()), None)
    if not ps or not pl:
        return []
    names = {}
    for row in _download_rows(H, pl):
        pid = row.get("provider_id")
        if pid:
            names[pid] = (row.get("holding_company") or row.get("provider_name") or "").strip()
    provs = []
    for r in _download_rows(H, ps):
        if r.get("geography_id") != BURTON_GEOID or r.get("data_type") != "Fixed Broadband":
            continue
        coverage = round(100 * float(r.get("res_st_pct") or 0), 1)
        if coverage <= 0:           # drop business-only / no-residential providers
            continue
        raw_name = names.get(r["provider_id"], "")
        provs.append({
            "name": BRANDS.get(raw_name, raw_name) or "(unknown provider)",
            "pct": coverage,
            "satellite": any(h in raw_name.lower() for h in SATELLITE_HINTS),
        })
    provs.sort(key=lambda p: -p["pct"])
    return provs


def fetch_adoption(census_key: str | None) -> float | None:
    """% of Burton households that actually subscribe to broadband (Census ACS 2023
    B28002_004E "broadband of any type" / B28002_001E total households). Needs a key."""
    if not census_key:
        return None
    url = ("https://api.census.gov/data/2023/acs/acs5?get=B28002_001E,B28002_004E"
           f"&for=place:12060&in=state:26&key={census_key}")
    try:
        data = json.loads(_get(url, {"User-Agent": "Mozilla/5.0"}, 45))
        total, broadband = int(data[1][0]), int(data[1][1])
        return round(100 * broadband / total, 1) if total > 0 else None
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default=os.environ.get("FCC_USERNAME"),
                    help="FCC API username (registration email)")
    ap.add_argument("--token", default=os.environ.get("FCC_HASH"),
                    help="FCC API token / hash value")
    ap.add_argument("--census-key", default=os.environ.get("CENSUS_API_KEY"),
                    help="Census API key (for the broadband-adoption stat; optional)")
    args = ap.parse_args()
    if not args.user or not args.token:
        sys.exit("FCC API needs BOTH a username and a token (set --user/--token or "
                 "FCC_USERNAME/FCC_HASH). Free signup: https://bdc.fcc.gov/")
    H = {"User-Agent": "Mozilla/5.0", "username": args.user, "hash_value": args.token}

    # Latest availability as-of date.
    dates = json.loads(_get(f"{API}/listAsOfDates", H, 45))["data"]
    as_of = max(d["as_of_date"] for d in dates if d["data_type"] == "availability")

    # Find the Michigan fixed-broadband place-summary file for that date.
    files = json.loads(_get(f"{API}/downloads/listAvailabilityData/{as_of}", H))["data"]
    match = next((f for f in files
                  if f.get("subcategory") == "Summary by Geography Type - Census Place"
                  and f"_{STATE_FIPS}_fixed_broadband_summary_by_geography_place" in (f.get("file_name") or "")), None)
    if not match:
        sys.exit(f"No MI place-summary file found for {as_of}")

    raw = _get(f"{API}/downloads/downloadFile/availability/{match['file_id']}", H)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))

    # Residential rows for Burton.
    burton = [r for r in rows if r.get("geography_id") == BURTON_GEOID and r.get("biz_res") == "R"]
    if not burton:
        sys.exit(f"No Burton ({BURTON_GEOID}) residential rows in the MI file")
    by_tech = {r["technology"]: r for r in burton}
    any_tech = by_tech.get("Any Technology")
    if not any_tech:
        sys.exit("No 'Any Technology' row for Burton")

    def pct(row, col):
        try:
            return round(100 * float(row[col]), 1)
        except (TypeError, ValueError, KeyError):
            return 0.0

    homes = int(any_tech.get("total_units") or 0)
    served_100_20 = pct(any_tech, "speed_100_20")
    gig = pct(any_tech, "speed_1000_100")

    stats = [
        {"label": "Broadband-serviceable homes", "value": f"{homes:,}",
         "hint": f"FCC, {as_of}"},
        {"label": "Have 100/20 Mbps access", "value": f"{served_100_20:g}%",
         "hint": "FCC broadband benchmark"},
        {"label": "Have 250/25 Mbps", "value": f"{pct(any_tech, 'speed_250_25'):g}%"},
        {"label": "Have gigabit access", "value": f"{gig:g}%",
         "hint": "1000/100 Mbps"},
    ]

    charts = [
        {"type": "bars", "title": "Home internet availability by speed", "unit": "%",
         "series": [{"label": lab, "value": pct(any_tech, col)} for col, lab in SPEED_TIERS]},
    ]
    # Coverage by technology at the 100/20 benchmark. Keep clean single
    # technologies; drop composite ("All ...", "Any ...", "Cable/Fiber") and
    # satellite rows (satellite is ~100% everywhere, so it isn't informative here).
    def is_composite(t: str) -> bool:
        tl = t.lower()
        return (t.startswith(("All ", "Any ")) or "/" in t
                or "satellite" in tl or "gso" in tl)
    tech_rows = [(t, pct(r, "speed_100_20")) for t, r in by_tech.items()
                 if not is_composite(t)]
    tech_rows = sorted((t for t in tech_rows if t[1] > 0), key=lambda x: -x[1])
    if tech_rows:
        charts.append({
            "type": "bars", "title": "Availability by technology (100/20 Mbps)", "unit": "%",
            "series": [{"label": t, "value": v} for t, v in tech_rows],
        })

    # Provider competition (FCC public Provider Summary) + adoption (Census ACS).
    providers = build_providers(files, H)
    terrestrial = [p for p in providers if not p["satellite"]]
    satellite = [p for p in providers if p["satellite"]]
    if providers:
        stats.append({"label": "Home-internet providers", "value": str(len(providers)),
                      "hint": f"{len(terrestrial)} wired/wireless + {len(satellite)} satellite"})
    adoption = fetch_adoption(args.census_key)
    if adoption is not None:
        stats.append({"label": "Households with broadband", "value": f"{adoption:g}%",
                      "hint": "actually subscribe (Census ACS)"})
    if terrestrial:
        charts.append({
            "type": "bars", "title": "Where each provider reaches (% of Burton homes)", "unit": "%",
            "series": [{"label": p["name"], "value": p["pct"]} for p in terrestrial],
        })

    notes = [
        "Availability = where service can be ordered (reported by providers), not "
        "actual speeds or price, the FCC collects no pricing data.",
        "\"Broadband\" is the FCC benchmark of 100/20 Mbps. Speed figures are the share "
        "of broadband-serviceable homes with reported access at each speed.",
    ]
    if satellite:
        notes.append("Satellite (" + ", ".join(p["name"] for p in satellite) + ") reaches "
                     "all of Burton, so it is counted but not charted with the wired/wireless "
                     "providers most homes actually choose between.")
    if adoption is not None:
        notes.append("\"Households with broadband\" is actual subscriptions (US Census ACS "
                     "2023), a different measure than availability. Not endorsed by the Census Bureau.")
    notes.append("Source: FCC National Broadband Map. This product is not endorsed or "
                 "certified by the FCC.")

    panel = {
        "title": "Broadband Access",
        "subtitle": f"Home internet availability in Burton: FCC National Broadband Map ({as_of})",
        "stats": stats,
        "charts": charts,
        "source": f"FCC National Broadband Map (Broadband Data Collection), fixed "
                  f"residential availability, Burton city, as of {as_of}.",
        "links": [{"text": "Look up your address on the FCC National Broadband Map",
                   "href": f"https://broadbandmap.fcc.gov/area-summary/fixed?type=place&geoid={BURTON_GEOID}"}],
        "notes": notes,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT}")
    print(f"  as_of={as_of} homes={homes:,} 100/20={served_100_20}% gigabit={gig}%")
    print(f"  by tech (100/20): {tech_rows}")
    print(f"  providers={len(providers)} (terrestrial={len(terrestrial)}, satellite={len(satellite)}); "
          f"adoption={adoption}")
    for p in providers:
        print(f"    {p['pct']:5.1f}%  {'[sat] ' if p['satellite'] else ''}{p['name']}")


if __name__ == "__main__":
    main()
