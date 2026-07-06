# Build public/info-roadsafety.json: a Roadway Safety dashboard from historical
# Genesee County (GCMPC) crash records for the City of Burton.
#
# Source: GCMPC "Crash_Locations_2014_2018" FeatureServer (RoadSoft / Michigan
# State Police UD-10 crash data), filtered to CITY='Burton'. Public county data.
#
# DASHBOARD ONLY (no map overlay): the data is 2014-2018: 7-11 years old: so it
# is presented as a historical trend/summary, NOT a live "where crashes happen now"
# map (road changes since, e.g. new roundabouts, would make a current-looking
# hotspot map misleading).
#
# Re-runnable (committed output; the site reads the JSON, never ArcGIS):
#     python tools/extract_crashes.py
#
# Stdlib only (tools/lib helpers over urllib/json).
from __future__ import annotations

import sys
from collections import Counter

from lib.arcgis import paged_query
from lib.iox import write_json
from lib.paths import public_path

OUT_INFO = public_path("info-roadsafety.json")

LAYER = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
         "Crash_Locations_2014_2018/FeatureServer/0/query")
WHERE = "CITY='Burton'"
PAGE = 2000

SEV_COLOR = {"Fatal": "#c0392b", "Injury": "#e08a00", "Property Damage Only": "#4ea735"}
SEV_FALLBACK = "#888888"
SEV_ORDER = ["Fatal", "Injury", "Property Damage Only"]


def fetch() -> list:
    fields = ("YEAR,CRASHSEVER,CRASHTYPE,NUMOFINJ,NUMOFKILL,PRNAME,INTERNAME,"
              "PEDESTRIAN,BIKE,MOTORCYCLE,DRINKING")
    params = {
        "where": WHERE,
        "outFields": fields,
        "returnGeometry": "false",
        "orderByFields": "YEAR",
        "f": "json",
    }
    return [f["attributes"] for f in paged_query(LAYER, params, page_size=PAGE, timeout=120)]


def _yes(v) -> bool:
    return str(v).strip().lower() == "yes"


def main() -> int:
    rows = fetch()
    if not rows:
        raise SystemExit("No Burton crash records returned.")

    total = len(rows)
    by_year = Counter(a.get("YEAR") for a in rows if a.get("YEAR"))
    sev = Counter(a.get("CRASHSEVER") or "Unknown" for a in rows)
    killed = sum(a.get("NUMOFKILL") or 0 for a in rows)
    injured = sum(a.get("NUMOFINJ") or 0 for a in rows)
    fatal_crashes = sev.get("Fatal", 0)
    injury_crashes = sev.get("Injury", 0)
    ctype = Counter((a.get("CRASHTYPE") or "Other").strip() for a in rows)
    ped = sum(1 for a in rows if _yes(a.get("PEDESTRIAN")))
    bike = sum(1 for a in rows if _yes(a.get("BIKE")))
    moto = sum(1 for a in rows if _yes(a.get("MOTORCYCLE")))
    drink = sum(1 for a in rows if _yes(a.get("DRINKING")))

    years = sorted(by_year)
    span = f"{years[0]}-{years[-1]}" if years else "n/a"
    full_years = [y for y in years if by_year[y] >= 100]  # exclude partial-year tails
    avg_per_year = round(sum(by_year[y] for y in full_years) / len(full_years)) if full_years else 0

    # Crash hotspots: most frequent primary/intersecting street pairs.
    inter = Counter()
    for a in rows:
        p = (a.get("PRNAME") or "").strip().title()
        i = (a.get("INTERNAME") or "").strip().title()
        if p and i and i.lower() not in ("", "uncoded & errors"):
            inter[" & ".join(sorted([p, i]))] += 1

    stats = [
        {"label": "Crashes recorded", "value": f"{total:,}", "hint": f"{span} (all severities)"},
        {"label": "Injury crashes", "value": f"{injury_crashes:,}",
         "hint": f"{injured:,} people injured"},
        {"label": "Fatal crashes", "value": str(fatal_crashes),
         "hint": f"{killed} lives lost ({span})"},
        {"label": "Most common type", "value": ctype.most_common(1)[0][0] if ctype else "n/a",
         "hint": f"{round(100 * ctype.most_common(1)[0][1] / total)}% of crashes" if ctype else ""},
        {"label": "Typical crashes / year", "value": f"{avg_per_year:,}",
         "hint": "full years on record"},
    ]

    charts = [
        {"type": "bars", "title": "Crashes by year", "unit": "",
         "series": [{"label": str(y), "value": by_year[y]} for y in years]},
        {"type": "donut", "title": "Crashes by severity",
         "series": [{"label": k, "value": sev[k], "color": SEV_COLOR.get(k, SEV_FALLBACK)}
                    for k in SEV_ORDER if sev.get(k)]},
        {"type": "bars", "title": "Most common crash types", "unit": "",
         "series": [{"label": k, "value": v} for k, v in ctype.most_common(6)]},
    ]

    table = {
        "title": "Most frequent crash locations",
        "columns": ["Intersection", "Crashes"],
        "rows": [{"cells": [name, str(c)]} for name, c in inter.most_common(12)],
    }

    panel = {
        "title": "Roadway Safety",
        "subtitle": f"Reported traffic crashes in Burton, {span}",
        "stats": stats,
        "charts": charts,
        "tables": [table],
        "source": (f"Genesee County (GCMPC) crash records (Michigan State Police UD-10 / RoadSoft), "
                   f"City of Burton, {span}."),
        "links": [
            {"text": "Michigan Traffic Crash Facts", "href": "https://www.michigantrafficcrashfacts.org/"},
            {"text": "Roads & Pavement dashboard", "href": "#roads"},
        ],
        "notes": [
            f"This is HISTORICAL data ({span}): a multi-year summary and trend, not a live or "
            "current crash map. Road and intersection changes since then (new signals, the "
            "Bristol/Belsay roundabout, resurfacing) mean today's pattern can differ.",
            "Counts are crash reports where the recorded city is Burton; most crashes are "
            "property-damage-only. \"Fatal\" and \"injury\" count crashes in which someone was "
            "killed or injured.",
            "Source: Genesee County (GCMPC) / Michigan State Police UD-10 crash data; provided for "
            "public awareness, not endorsed by the City of Burton.",
        ],
    }
    write_json(OUT_INFO, panel)

    print(f"Wrote {OUT_INFO}")
    print(f"  {total} crashes {span}; by year {dict(sorted(by_year.items()))}")
    print(f"  severity {dict(sev)}; killed={killed} injured={injured}")
    print(f"  ped={ped} bike={bike} moto={moto} drinking={drink}")
    print(f"  top spot: {inter.most_common(1)[0] if inter else None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
