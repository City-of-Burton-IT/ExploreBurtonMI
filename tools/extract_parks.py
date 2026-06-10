# Build public/parks.geojson + public/info-parks.json: parks within the City of
# Burton, as a map overlay (park boundaries) + a small dashboard.
#
# Source: Genesee County (GCMPC) public "Genesee_County_Parks" FeatureServer
# (Name, ParkType, OwnedBy, Acreage). County-wide; we keep parks whose footprint
# centers inside the Burton boundary (the bbox alone pulls in many Flint parks).
# Public county GIS data.
#
# This complements the curated park *points* in the map's facilities layer with the
# actual park *boundaries*.
#
# Re-runnable (committed output; the site reads the JSON/GeoJSON, never ArcGIS):
#     python tools/extract_parks.py
#
# Stdlib only (urllib/json).
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
OUT_GEOJSON = os.path.join(ROOT, "public", "parks.geojson")
OUT_INFO = os.path.join(ROOT, "public", "info-parks.json")

LAYER = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
         "Genesee_County_Parks/FeatureServer/0/query")

# Broad owner category -> color (matches a "who runs it" reading).
def _category(park_type: str, owned_by: str) -> str:
    t = f"{park_type} {owned_by}".lower()
    if "burton" in t:
        return "City of Burton"
    if "county" in t:
        return "Genesee County"
    if "neighborhood" in t:
        return "Neighborhood"
    return "Other"


CAT_COLOR = {
    "City of Burton": "#2e7d32",   # green
    "Genesee County": "#1565c0",   # blue
    "Neighborhood": "#4ea735",     # light green
    "Other": "#6a1b9a",            # purple
}
CAT_FALLBACK = "#888888"
CAT_ORDER = ["City of Burton", "Genesee County", "Neighborhood", "Other"]


def _round(coords, ndigits=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], ndigits), round(coords[1], ndigits)]
    return [_round(c, ndigits) for c in coords]


def _rings() -> list:
    gj = json.load(open(BOUNDARY, encoding="utf-8"))
    geom = gj["geometry"] if gj.get("type") == "Feature" else (
        gj["features"][0]["geometry"] if gj.get("features") else gj)
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [ring for poly in polys for ring in poly]


def _inside(lon: float, lat: float, rings: list) -> bool:
    ins = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                ins = not ins
            j = i
    return ins


def _centroid(geom: dict):
    """Rough centroid: mean of all vertices. Good enough to decide which city a
    compact park sits in."""
    pts = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for sub in c:
                walk(sub)

    walk(geom.get("coordinates", []))
    if not pts:
        return None
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def fetch() -> list:
    params = {
        "where": "1=1",
        "outFields": "Name,ParkType,OwnedBy,Acreage",
        "geometry": "-83.72,42.93,-83.54,43.08",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outSR": "4326",
        "maxAllowableOffset": "0.00008",
        "returnGeometry": "true",
        "f": "geojson",
    }
    url = LAYER + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp).get("features", [])


def main() -> int:
    rings = _rings()
    raw = fetch()
    if not raw:
        raise SystemExit("No parks returned from the county service.")

    features = []
    cat_acres: dict[str, float] = defaultdict(float)
    cat_count: dict[str, int] = defaultdict(int)
    parks: list[tuple] = []

    for f in raw:
        geom = f.get("geometry")
        a = f.get("properties", {}) or {}
        if not geom:
            continue
        c = _centroid(geom)
        if not c or not _inside(c[0], c[1], rings):
            continue  # park does not sit inside Burton
        name = (a.get("Name") or "Park").strip() or "Park"
        ptype = (a.get("ParkType") or "").strip()
        owner = (a.get("OwnedBy") or "").strip()
        acres = round(a.get("Acreage") or 0, 1)
        cat = _category(ptype, owner)
        cat_acres[cat] += acres
        cat_count[cat] += 1
        parks.append((name, ptype or "Park", acres, cat))
        rows = [["Type", ptype or "Park"]]
        if owner and owner != ptype:
            rows.append(["Owner", owner])
        if acres:
            rows.append(["Size", f"{acres:g} acres"])
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "category": cat,
                "_color": CAT_COLOR.get(cat, CAT_FALLBACK),
                "_fillOpacity": 0.45,
                "_weight": 1,
                "_popupRows": rows,
            },
            "geometry": {"type": geom["type"], "coordinates": _round(geom["coordinates"])},
        })

    if not features:
        raise SystemExit("No parks fall inside Burton.")

    fc = {
        "type": "FeatureCollection",
        "_source": ("Genesee County parks (GCMPC Genesee_County_Parks), park footprints whose "
                    "center lies within the City of Burton, colored by who runs the park."),
        "features": features,
    }
    with open(OUT_GEOJSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

    # ---- dashboard -------------------------------------------------------
    total_ac = round(sum(cat_acres.values()))
    n = len(parks)
    biggest = max(parks, key=lambda p: p[2]) if parks else None

    stats = [
        {"label": "Parks in Burton", "value": str(n), "hint": "with a footprint in the city"},
        {"label": "Total park acres", "value": f"{total_ac:,}", "hint": "all parks combined"},
        {"label": "Largest park", "value": biggest[0] if biggest else "n/a",
         "hint": f"{biggest[2]:g} acres" if biggest else ""},
        {"label": "City of Burton parks", "value": str(cat_count.get("City of Burton", 0)),
         "hint": f"{round(cat_acres.get('City of Burton', 0))} acres city-run"},
    ]
    charts = [
        {"type": "donut", "title": "Park acres by who runs it",
         "series": [{"label": k, "value": round(cat_acres[k]), "color": CAT_COLOR.get(k, CAT_FALLBACK)}
                    for k in CAT_ORDER if cat_acres.get(k, 0) >= 0.5]},
    ]
    table_rows = [{
        "cells": [p[0], p[1], f"{p[2]:g}"],
        "color": CAT_COLOR.get(p[3], CAT_FALLBACK),
    } for p in sorted(parks, key=lambda p: p[2], reverse=True)]

    panel = {
        "title": "Parks",
        "subtitle": "Public parks and green space in Burton",
        "stats": stats,
        "charts": charts,
        "tables": [{
            "title": "Parks in Burton",
            "columns": ["Park", "Type", "Acres"],
            "rows": table_rows,
        }],
        "source": ("Genesee County parks dataset (GCMPC), park footprints within the City of Burton."),
        "links": [
            {"text": "Burton Parks & Recreation",
             "href": "https://www.burtonmi.gov/departments/parks_and_recreation/index.php"},
            {"text": "Genesee County Parks", "href": "https://www.geneseecountyparks.org/"},
        ],
        "notes": [
            "Turn on the \"Parks\" map overlay to see park boundaries. Acreage is the park's full "
            "size from the county dataset; for a park on the city edge, part of that area may extend "
            "beyond Burton.",
            "Includes city, county and neighborhood parks whose footprint centers in Burton. Park "
            "buildings and offices also appear as pins in the main map's Parks & Recreation category.",
            "Source: Genesee County (GCMPC) parks dataset; a regional GIS layer, not a live city "
            "facilities list.",
        ],
    }
    with open(OUT_INFO, "w", encoding="utf-8") as fh:
        json.dump(panel, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"Wrote {OUT_GEOJSON} ({len(features)} parks)")
    print(f"Wrote {OUT_INFO}")
    print(f"  {n} parks, {total_ac} ac; by category: { {k: (cat_count[k], round(cat_acres[k])) for k in cat_count} }")
    print(f"  largest: {biggest[0]} ({biggest[2]:g} ac)" if biggest else "")
    print(f"  geojson size: {os.path.getsize(OUT_GEOJSON)//1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
