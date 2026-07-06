# Build public/zoning.geojson + public/info-zoning.json: the City of Burton's
# zoning districts, as an ACCURATE map overlay (replacing the approximate
# georeferenced zoning-map.jpg) + a dashboard.
#
# Source: Genesee County (GCMPC) public "Zoning_Layer" FeatureServer, filtered to
# CVT = 'City of Burton'. Carries the city's zoning districts (Zoning code,
# ZoneDescr, ZoningCat) compiled from the City of Burton 2017 zoning map. Public
# county GIS data.
#
# This resolves issue #18: the previous overlay was the scanned zoning map
# georeferenced by bounds (approximate); these are true district polygons.
#
# Re-runnable (committed output; the site reads the JSON/GeoJSON, never ArcGIS):
#     python tools/extract_zoning.py
#
# Uses tools/lib for HTTP paging + writes.
from __future__ import annotations

import os
import sys
from collections import defaultdict

from lib.arcgis import paged_query
from lib.geo import round_coords
from lib.iox import write_geojson, write_json
from lib.paths import public_path

OUT_GEOJSON = public_path("zoning.geojson")
OUT_INFO = public_path("info-zoning.json")

LAYER = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
         "Zoning_Layer/FeatureServer/0/query")
WHERE = "CVT='City of Burton'"
PAGE = 2000

# Conventional zoning-map colors by broad category.
CAT_COLOR = {
    "Residential": "#f2c84b",  # yellow
    "Commercial": "#d9534f",   # red
    "Office": "#4a78b5",       # blue
    "Industrial": "#9b6fb0",   # purple
    "Parking": "#9e9e9e",      # grey
}
CAT_FALLBACK = "#888888"
# Display order for the dashboard (largest/most relevant first; matches the legend).
CAT_ORDER = ["Residential", "Commercial", "Office", "Industrial", "Parking"]


def fetch() -> list:
    params = {
        "where": WHERE,
        "outFields": "Zoning,ZoneDescr,ZoningCat,AcreCalc,DataYear",
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": "0.00005",  # ~5 m generalization (keeps parcel shapes)
        "f": "geojson",
    }
    return list(paged_query(LAYER, params, page_size=PAGE, timeout=120))


def main() -> int:
    raw = fetch()
    if not raw:
        raise SystemExit("No City of Burton zoning polygons returned.")

    features = []
    cat_acres: dict[str, float] = defaultdict(float)
    code_acres: dict[str, float] = defaultdict(float)
    code_meta: dict[str, tuple] = {}
    years: set[str] = set()

    for f in raw:
        geom = f.get("geometry")
        a = f.get("properties", {}) or {}
        if not geom:
            continue
        code = (a.get("Zoning") or "?").strip() or "?"
        descr = (a.get("ZoneDescr") or "").strip().title()
        cat = (a.get("ZoningCat") or "Other").strip() or "Other"
        acres = a.get("AcreCalc") or 0
        if a.get("DataYear"):
            years.add(str(a["DataYear"]))
        cat_acres[cat] += acres
        code_acres[code] += acres
        code_meta[code] = (descr, cat)
        name = f"{code} - {descr}" if descr else code
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "category": cat,
                "_color": CAT_COLOR.get(cat, CAT_FALLBACK),
                "_fillOpacity": 0.4,
                "_weight": 1,
                "_popupRows": [["Category", cat]],
            },
            "geometry": {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])},
        })

    fc = {
        "type": "FeatureCollection",
        "_source": ("City of Burton zoning districts (GCMPC Zoning_Layer, City of Burton 2017 "
                    "zoning map), colored by district category."),
        "features": features,
    }
    write_geojson(OUT_GEOJSON, fc)

    # ---- dashboard -------------------------------------------------------
    total_ac = round(sum(cat_acres.values()))
    res_share = round(100 * cat_acres.get("Residential", 0) / total_ac) if total_ac else 0
    n_codes = len([c for c in code_acres if c != "?"])
    vintage = "/".join(sorted(years)) if years else "n/a"

    stats = [
        {"label": "Zoned acres", "value": f"{total_ac:,}", "hint": "within the city"},
        {"label": "Zoning districts", "value": str(n_codes), "hint": "distinct codes"},
        {"label": "Residential", "value": f"{res_share}%", "hint": "of zoned land"},
        {"label": "Map vintage", "value": vintage, "hint": "City zoning map"},
    ]

    cat_series = [{"label": k, "value": round(cat_acres[k]), "color": CAT_COLOR.get(k, CAT_FALLBACK)}
                  for k in CAT_ORDER if cat_acres.get(k, 0) >= 0.5]
    # any categories not in the known order
    for k in sorted(cat_acres, key=lambda k: -cat_acres[k]):
        if k not in CAT_ORDER and cat_acres[k] >= 0.5:
            cat_series.append({"label": k, "value": round(cat_acres[k]), "color": CAT_FALLBACK})

    charts = [
        {"type": "donut", "title": "Zoned land by category (acres)", "series": cat_series},
        {"type": "bars", "title": "Largest districts (acres)", "unit": " ac",
         "series": [{"label": c, "value": round(code_acres[c])}
                    for c in sorted(code_acres, key=lambda c: -code_acres[c])[:8] if c != "?"]},
    ]

    table_rows = []
    for c in sorted(code_acres, key=lambda c: -code_acres[c]):
        if c == "?":
            continue
        descr, cat = code_meta[c]
        table_rows.append({
            "cells": [c, descr or "n/a", cat, f"{round(code_acres[c]):,}"],
            "color": CAT_COLOR.get(cat, CAT_FALLBACK),
        })

    panel = {
        "title": "Zoning",
        "subtitle": "How land in Burton is zoned: the city's zoning districts",
        "stats": stats,
        "charts": charts,
        "tables": [{
            "title": "Zoning districts",
            "columns": ["Code", "District", "Category", "Acres"],
            "rows": table_rows,
        }],
        "source": ("City of Burton zoning map (via the Genesee County GCMPC Zoning_Layer); "
                   "zoning districts within the city."),
        "links": [
            {"text": "Burton zoning division (DPW)",
             "href": "https://www.burtonmi.gov/departments/department_of_public_works/zoning_division.php"},
        ],
        "notes": [
            "Turn on the \"Zoning\" map overlay to see these districts on the map: each area is "
            "colored by category (residential, commercial, office, industrial). Tap an area for its "
            "district code.",
            f"From the City of Burton {vintage} zoning map. Zoning is the legal land-use designation, "
            "which is not the same as how a parcel is currently used. For the authoritative, current "
            "district of a specific property, contact the Burton zoning division.",
            "Source: GCMPC Zoning_Layer (City of Burton); a regional GIS dataset, not a live city "
            "zoning lookup.",
        ],
    }
    write_json(OUT_INFO, panel)

    print(f"Wrote {OUT_GEOJSON} ({len(features)} polygons)")
    print(f"Wrote {OUT_INFO}")
    print(f"  total {total_ac:,} ac; categories: { {k: round(v) for k, v in cat_acres.items()} }")
    print(f"  districts: {n_codes}; vintage {vintage}; geojson {os.path.getsize(OUT_GEOJSON)//1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
