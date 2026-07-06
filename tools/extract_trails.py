# Build public/trails.geojson + public/info-trails.json: the trails, shared-use
# paths and non-motorized facilities serving the City of Burton.
#
# Source: Genesee County's "Legacy Trail Map" web map (the county MPO / GCMPC
# non-motorized plan), layer 0 "Major Trail Segments", in the official Genesee
# County ArcGIS organization (services2.arcgis.com/5ckbIY7K9TUKoseK). Public
# county planning data. Segments are county-wide; we keep the ones whose path
# passes through Burton and report length CLIPPED to the city (LENMILES is the
# full-segment length, much of which can lie outside Burton).
#
# STATUS is reported honestly: "Existing" trails are built and usable; "Under
# Construction", "Programmed" and "Proposed" are planned: drawn dashed on the
# map and counted separately, never shown as if already built.
#
# Re-runnable (committed output; the site reads the JSON/GeoJSON, never ArcGIS):
#     python tools/extract_trails.py
#
# Uses tools/lib for HTTP + writes.
from __future__ import annotations

import json
import os
import math
import sys
from collections import defaultdict

from lib.geo import round_coords
from lib.httpio import get_json
from lib.iox import write_geojson, write_json
from lib.paths import public_path

BOUNDARY = public_path("boundary.geojson")
OUT_GEOJSON = public_path("trails.geojson")
OUT_INFO = public_path("info-trails.json")

LAYER = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/arcgis/rest/services/"
         "Legacy_Trail_Map_WFL1/FeatureServer/0/query")

# Built vs planned. "Existing" is the only built status; the rest are planned and
# get a dashed line + a separate tally.
EXISTING = "Existing"
PLANNED_ORDER = ["Under Construction", "Programmed", "Proposed"]
STATUS_COLOR = {
    "Existing": "#2e7d32",           # green = built / usable
    "Under Construction": "#e08a00",  # amber
    "Programmed": "#1565c0",          # blue = planned/funded
    "Proposed": "#6a1b9a",            # purple = proposed
}
DEFAULT_COLOR = "#1565c0"


def _rings() -> list:
    gj = json.load(open(BOUNDARY, encoding="utf-8"))
    geom = gj["geometry"] if gj.get("type") == "Feature" else (
        gj["features"][0]["geometry"] if gj.get("features") else gj)
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [ring for poly in polys for ring in poly]


def _bbox(rings: list, pad: float = 0.004) -> tuple:
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


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


def _haversine_mi(a: list, b: list) -> float:
    """Great-circle distance between [lon,lat] points, in miles."""
    r = 3958.7613
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _parts(geom: dict) -> list:
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


def _clipped_miles(geom: dict, rings: list) -> float:
    """Length of the portion of a (multi)line that lies inside Burton, in miles.
    Each vertex-to-vertex sub-segment is densified and a sub-piece is counted when
    its midpoint is inside the boundary, a good approximation of true clipping
    without a polygon-line intersection library (segments here are densely
    vertexed). Avoids overcounting trails that run far past the city."""
    total = 0.0
    for part in _parts(geom):
        for i in range(len(part) - 1):
            a, b = part[i], part[i + 1]
            seg_mi = _haversine_mi(a, b)
            if seg_mi == 0:
                continue
            steps = max(1, int(seg_mi / 0.02))  # ~0.02 mi (~30 m) sampling
            for s in range(steps):
                t0 = s / steps
                t1 = (s + 1) / steps
                mx = a[0] + (b[0] - a[0]) * (t0 + t1) / 2
                my = a[1] + (b[1] - a[1]) * (t0 + t1) / 2
                if _inside(mx, my, rings):
                    total += seg_mi / steps
    return total


def _touches(geom: dict, rings: list, bbox: tuple) -> bool:
    for part in _parts(geom):
        for lon, lat in part:
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3] and _inside(lon, lat, rings):
                return True
    return False


def fetch() -> list:
    params = {
        "where": "1=1",
        "outFields": "NAMELOCAL,LegTrail,STATUS,TRAILTYP,SurfaceType,Network,LENMILES",
        "outSR": "4326",
        "returnGeometry": "true",
        "f": "geojson",
    }
    return get_json(LAYER, params, timeout=120).get("features", [])


def main() -> int:
    rings = _rings()
    bbox = _bbox(rings)
    raw = fetch()
    if not raw:
        raise SystemExit("No trail segments returned (check the Legacy Trail Map service).")

    features = []
    # Per-named-trail aggregation (clipped miles), and category tallies.
    by_name: dict[str, dict] = {}
    miles_status: dict[str, float] = defaultdict(float)
    miles_type: dict[str, float] = defaultdict(float)
    miles_surface: dict[str, float] = defaultdict(float)

    for f in raw:
        geom = f.get("geometry")
        props = f.get("properties", {}) or {}
        if not geom or not _touches(geom, rings, bbox):
            continue
        miles = round(_clipped_miles(geom, rings), 2)
        if miles <= 0:
            continue  # only touches the boundary in passing; no real Burton length
        status = (props.get("STATUS") or "Unknown").strip() or "Unknown"
        ttype = (props.get("TRAILTYP") or "Path").strip() or "Path"
        surface = (props.get("SurfaceType") or "Unknown").strip() or "Unknown"
        name = (props.get("NAMELOCAL") or props.get("LegTrail") or "Unnamed trail").strip()
        is_existing = status == EXISTING

        miles_status[status] += miles
        miles_type[ttype] += miles
        miles_surface[surface] += miles
        agg = by_name.setdefault(name, {"miles": 0.0, "status": status, "type": ttype,
                                        "surface": surface, "existing": is_existing})
        agg["miles"] += miles
        # Prefer to label a named trail by its existing portion if any segment is built.
        if is_existing:
            agg["existing"] = True
            agg["status"] = EXISTING

        rows = [["Status", status], ["Type", ttype]]
        if surface and surface != "Unknown":
            rows.append(["Surface", surface])
        rows.append(["In Burton", f"{miles:.2f} mi"])
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "status": status,
                "_color": STATUS_COLOR.get(status, DEFAULT_COLOR),
                "_weight": 4 if is_existing else 3,
                # planned trails are drawn dashed so they never read as built
                "_dashArray": None if is_existing else "6 6",
                "_popupRows": rows,
            },
            "geometry": {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])},
        })

    if not features:
        raise SystemExit("No trail segments fall inside Burton.")

    # Draw existing first so planned/dashed lines layer on top where they overlap.
    features.sort(key=lambda f: (f["properties"]["status"] != EXISTING,
                                 f["properties"]["name"]))

    fc = {
        "type": "FeatureCollection",
        "_source": ("Genesee County 'Legacy Trail Map' (GCMPC non-motorized plan), Major Trail "
                    "Segments. Segments serving the City of Burton; lengths clipped to the city. "
                    "Existing trails are solid; planned (programmed/proposed/under construction) "
                    "are dashed."),
        "features": features,
    }
    write_geojson(OUT_GEOJSON, fc)

    # ---- dashboard JSON --------------------------------------------------
    existing_mi = round(miles_status.get(EXISTING, 0.0), 1)
    planned_mi = round(sum(v for k, v in miles_status.items() if k != EXISTING), 1)
    existing_names = sorted((n for n, a in by_name.items() if a["existing"]),
                            key=lambda n: by_name[n]["miles"], reverse=True)
    longest = existing_names[0] if existing_names else None

    stats = [
        {"label": "Existing trail miles in Burton", "value": f"{existing_mi:g}",
         "hint": "built & usable today"},
        {"label": "Named trails serving Burton", "value": str(len(by_name)),
         "hint": f"{len(existing_names)} with an existing segment"},
        {"label": "Longest existing trail", "value": longest or "n/a",
         "hint": f"{by_name[longest]['miles']:.1f} mi in Burton" if longest else ""},
        {"label": "Planned / programmed miles", "value": f"{planned_mi:g}",
         "hint": "proposed, programmed or under construction"},
    ]

    def _bars(d: dict, title: str, order: list | None = None) -> dict:
        items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)
        if order:
            items = sorted(d.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        return {"type": "bars", "title": title, "unit": " mi",
                "series": [{"label": k, "value": round(v, 1)} for k, v in items if v >= 0.05]}

    status_order = [EXISTING] + PLANNED_ORDER
    charts = [
        {"type": "donut", "title": "Trail miles by status (Burton)",
         "series": [{"label": k, "value": round(miles_status[k], 1),
                     "color": STATUS_COLOR.get(k, DEFAULT_COLOR)}
                    for k in status_order if miles_status.get(k, 0) >= 0.05]},
        _bars(miles_type, "Trail miles by type"),
        _bars(miles_surface, "Trail miles by surface"),
    ]

    table_rows = []
    for n in sorted(by_name, key=lambda n: by_name[n]["miles"], reverse=True):
        a = by_name[n]
        table_rows.append({
            "cells": [n, a["status"], a["type"], a["surface"] if a["surface"] != "Unknown" else "n/a",
                      f"{a['miles']:.2f}"],
            "color": STATUS_COLOR.get(a["status"], DEFAULT_COLOR),
        })

    panel = {
        "title": "Trails & Pathways",
        "subtitle": "Trails, shared-use paths and non-motorized routes serving Burton",
        "stats": stats,
        "charts": charts,
        "tables": [{
            "title": "Trails serving Burton",
            "columns": ["Trail", "Status", "Type", "Surface", "Miles in Burton"],
            "rows": table_rows,
        }],
        "source": ("Genesee County Metropolitan Planning Commission (GCMPC) Legacy Trail Map / "
                   "non-motorized plan, trail segments serving the City of Burton."),
        "links": [
            {"text": "Genesee County trails dashboard",
             "href": "https://gccountymi.maps.arcgis.com/apps/dashboards/882502c5000146ec8cafa9158a8e63c1"},
            {"text": "Iron Belle Trail (State of Michigan)",
             "href": "https://www.michigan.gov/dnr/things-to-do/iron-belle-trail"},
        ],
        "notes": [
            "Mileage is clipped to the City of Burton: a trail's full length (the county plan's "
            "LENMILES) often extends well beyond the city, so only the in-Burton portion is counted.",
            "\"Existing\" trails are built and usable today (drawn solid on the map). \"Under "
            "construction\", \"programmed\" and \"proposed\" routes are planned, not yet open "
            "(drawn dashed): shown so residents can see what's coming, not as if already built.",
            "Source: Genesee County (GCMPC) Legacy Trail Map; a regional planning dataset, not a "
            "City of Burton inventory.",
        ],
    }
    write_json(OUT_INFO, panel)

    print(f"Wrote {OUT_GEOJSON} ({len(features)} segments)")
    print(f"Wrote {OUT_INFO}")
    print(f"  existing in Burton: {existing_mi} mi across {len(existing_names)} trails; "
          f"planned: {planned_mi} mi; named trails: {len(by_name)}")
    print(f"  by status (mi): { {k: round(v,1) for k,v in miles_status.items()} }")
    print(f"  by type   (mi): { {k: round(v,1) for k,v in miles_type.items()} }")
    print(f"  geojson size: {os.path.getsize(OUT_GEOJSON) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
