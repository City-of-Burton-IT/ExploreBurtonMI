# Build public/paser-roads.geojson + public/info-roads.json: the pavement
# condition (PASER) of Burton's roads, as a map overlay + dashboard.
#
# Source: Genesee County (GCMPC) RoadSoft / PASER layer, in the official Genesee
# County ArcGIS organization (services2.arcgis.com/5ckbIY7K9TUKoseK), layer
# "PASER_Map_2025_WFL1/3", the most current (2024-25) ratings. Public county
# asset-management data.
#
# SCOPE: federal-aid eligible roads only (FEDAID=1), the network the state's
# Transportation Asset Management Council (TAMC) inspects on a fixed cycle. This
# is NOT every residential street; local/residential roads carry sparse, less
# reliable ratings (gravel roads in particular get default low scores), so they
# are deliberately excluded for a clean, comparable picture.
#
# PASER is a 1-10 surface rating. The standard TAMC grouping is used:
#   Good = 8-10, Fair = 5-7, Poor = 1-4. A 0 / null rating = Not Rated and is
#   EXCLUDED from the Good/Fair/Poor percentages (it is not a condition).
# "Poor" means the surface needs major repair/reconstruction, not that the road
# is closed or impassable.
#
# Burton's share is shown beside Genesee County's (same layer, same rule) so the
# numbers read as a regional reality, not a Burton-specific result. Statewide
# PASER is not in this county dataset, so the comparison is Burton vs the county.
#
# Re-runnable (committed output; the site reads the JSON/GeoJSON, never ArcGIS):
#     python tools/extract_paser.py
#
# Stdlib only (urllib/json).
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
OUT_GEOJSON = os.path.join(ROOT, "public", "paser-roads.geojson")
OUT_INFO = os.path.join(ROOT, "public", "info-roads.json")

LAYER = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
         "PASER_Map_2025_WFL1/FeatureServer/3/query")
WHERE = "FEDAID=1"
PAGE = 2000

COND_COLOR = {"Good": "#4ea735", "Fair": "#e08a00", "Poor": "#c0392b"}
COND_FALLBACK = "#888888"


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


def _parts(geom: dict) -> list:
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


def _rep_point(geom: dict):
    """A representative point on the line (its middle vertex). Burton federal-aid
    segments are short (~0.05-0.3 mi), so a midpoint-in-boundary test cleanly
    includes/excludes whole segments without per-segment clipping."""
    pts = [pt for part in _parts(geom) for pt in part]
    return pts[len(pts) // 2] if pts else None


def _group(rating) -> str | None:
    try:
        r = int(rating)
    except (TypeError, ValueError):
        return None
    if r <= 0:
        return None
    return "Good" if r >= 8 else "Fair" if r >= 5 else "Poor"


def _cond_pct(miles: dict) -> dict:
    """Good/Fair/Poor percentages over RATED miles (Not Rated excluded), matching
    how TAMC reports the split."""
    den = sum(v for k, v in miles.items() if k in ("Good", "Fair", "Poor"))
    return {k: round(100 * miles.get(k, 0) / den) for k in ("Good", "Fair", "Poor")} if den else {}


def fetch(with_geometry: bool, bbox: tuple | None = None) -> list:
    feats: list = []
    offset = 0
    fields = "CURRRATING,LENGTHMILE,PRNAME,SURFTYPE,AADT,AADT_YEAR,RATINGYEAR"
    while True:
        params = {
            "where": WHERE,
            "outFields": fields,
            "returnGeometry": "true" if with_geometry else "false",
            "outSR": "4326",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE),
            "f": "geojson" if with_geometry else "json",
        }
        if with_geometry and bbox:
            params.update({
                "geometry": ",".join(str(round(v, 5)) for v in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "maxAllowableOffset": "0.0001",  # ~10 m generalization, smaller file
            })
        url = LAYER + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            d = json.load(resp)
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return feats


def _attrs(f: dict, geo: bool) -> dict:
    return f["properties"] if geo else f["attributes"]


def main() -> int:
    rings = _rings()
    bbox = _bbox(rings)

    # Burton: federal-aid segments inside the city boundary (with geometry).
    burton_raw = fetch(with_geometry=True, bbox=bbox)
    burton = []
    for f in burton_raw:
        geom = f.get("geometry")
        if not geom:
            continue
        rp = _rep_point(geom)
        if rp and _inside(rp[0], rp[1], rings):
            burton.append(f)
    if not burton:
        raise SystemExit("No Burton federal-aid roads found inside the boundary.")

    # Genesee County: all federal-aid segments in the layer (no geometry needed).
    genesee_raw = fetch(with_geometry=False)

    def tally(rows: list, geo: bool):
        seg = Counter()
        miles = defaultdict(float)
        for f in rows:
            a = _attrs(f, geo)
            g = _group(a.get("CURRRATING"))
            key = g or "Not Rated"
            seg[key] += 1
            miles[key] += a.get("LENGTHMILE") or 0
        return seg, miles

    _, b_miles = tally(burton, True)
    _, g_miles = tally(genesee_raw, False)
    b_pct, g_pct = _cond_pct(b_miles), _cond_pct(g_miles)

    rated_mi = round(sum(b_miles[k] for k in ("Good", "Fair", "Poor")), 1)
    total_mi = round(sum(b_miles.values()), 1)

    # Busiest rated federal-aid road in Burton (highest AADT).
    def _adt(f):
        return _attrs(f, True).get("AADT") or 0
    rated_burton = [f for f in burton if _group(_attrs(f, True).get("CURRRATING"))]
    busiest = max(rated_burton, key=_adt) if rated_burton else None
    busiest_name = (_attrs(busiest, True).get("PRNAME") or "a road").strip() if busiest else "n/a"
    busiest_adt = _adt(busiest) if busiest else 0

    # Rating vintage (most ratings are 2024-25, with stragglers).
    years = Counter(_attrs(f, True).get("RATINGYEAR") for f in rated_burton)
    common_years = sorted(y for y, _ in years.most_common(2) if y)

    stats = [
        {"label": "Rated road-miles", "value": f"{rated_mi:g}",
         "hint": "federal-aid network in Burton"},
        {"label": "In good condition", "value": f"{b_pct.get('Good', 0)}%",
         "hint": "PASER 8-10"},
        {"label": "Needing major repair (poor)", "value": f"{b_pct.get('Poor', 0)}%",
         "hint": "PASER 1-4"},
        {"label": "Busiest rated road", "value": f"{busiest_adt:,}/day" if busiest_adt else "n/a",
         "hint": busiest_name},
        {"label": "Rated this cycle",
         "value": "/".join(str(y) for y in common_years) if common_years else "n/a",
         "hint": "PASER rating year"},
    ]

    charts = [
        {"type": "donut", "title": "Pavement condition (PASER, by road-mile)",
         "series": [{"label": k, "value": round(b_miles[k], 1), "color": COND_COLOR[k]}
                    for k in ("Good", "Fair", "Poor") if b_miles.get(k)]},
        {"type": "compare", "title": "How Burton compares: pavement condition",
         "rows": [{"label": f"{k} condition", "unit": "%", "values": [
             {"name": "Burton", "value": b_pct.get(k, 0)},
             {"name": "Genesee Co.", "value": g_pct.get(k, 0)},
         ]} for k in ("Good", "Fair", "Poor")]},
        {"type": "bars", "title": "Road-miles by surface", "unit": " mi",
         "series": _surface_series(burton)},
    ]

    # Per-road table: federal-aid roads aggregated by name, miles-weighted condition.
    table = _road_table(burton)

    vintage = "/".join(str(y) for y in common_years) if common_years else "recent"
    panel = {
        "title": "Roads & Pavement",
        "subtitle": "Burton's road pavement condition: Genesee County PASER ratings",
        "stats": stats,
        "charts": charts,
        "tables": [table],
        "source": (f"Genesee County Metropolitan Planning Commission (GCMPC) PASER pavement "
                   f"ratings (RoadSoft, {vintage}), federal-aid eligible roads within the City of "
                   f"Burton."),
        "links": [
            {"text": "Winter road maintenance (snow & ice plan)", "href": "#guide/snow-and-ice"},
            {"text": "Michigan TAMC dashboard", "href": "https://www.mcgi.state.mi.us/mappingforhealth/"},
            {"text": "GCMPC pavement conditions", "href": "https://www.gcmpc.org/"},
        ],
        "notes": [
            "PASER is a 1-10 surface rating. Good = 8-10, Fair = 5-7, Poor = 1-4. \"Poor\" means "
            "the surface needs major repair or reconstruction, not that a road is closed or "
            "impassable.",
            f"Covers federal-aid eligible roads only, the network the state's asset-management "
            f"council inspects on a cycle. It is NOT every residential street, so a resident may "
            f"not find their own street here. These ratings are from {vintage}.",
            f"Burton's split is shown beside Genesee County's, tallied from the same dataset by the "
            f"identical rule, so the picture reads as a regional reality (the county is "
            f"{g_pct.get('Poor', 0)}% poor by road-mile). Not-rated miles are excluded from the "
            f"percentages.",
            "Source: Genesee County (GCMPC) PASER / RoadSoft; a regional dataset, not endorsed by "
            "the City of Burton.",
        ],
    }

    # ---- write outputs ---------------------------------------------------
    feats = []
    for f in burton:
        a = _attrs(f, True)
        g = _group(a.get("CURRRATING"))
        cond = g or "Not Rated"
        name = (a.get("PRNAME") or "Road").strip() or "Road"
        rating = a.get("CURRRATING") or 0
        rows = [["Condition", cond]]
        if g:
            rows.append(["PASER rating", f"{int(rating)}/10"])
        surf = (a.get("SURFTYPE") or "").strip()
        if surf and surf != "Undefined":
            rows.append(["Surface", surf])
        ry = a.get("RATINGYEAR")
        if ry:
            rows.append(["Rated", str(ry)])
        feats.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "condition": cond,
                "_color": COND_COLOR.get(cond, COND_FALLBACK),
                "_weight": 4,
                "_popupRows": rows,
            },
            "geometry": {"type": f["geometry"]["type"], "coordinates": _round(f["geometry"]["coordinates"])},
        })
    fc = {
        "type": "FeatureCollection",
        "_source": ("Genesee County (GCMPC) PASER pavement ratings (2024-25), federal-aid roads "
                    "within the City of Burton, colored Good/Fair/Poor."),
        "features": feats,
    }
    with open(OUT_GEOJSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    with open(OUT_INFO, "w", encoding="utf-8") as fh:
        json.dump(panel, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # Re-apply the capital-projects link (a fresh fetch overwrote info-roads.json)
    # and rebuild the funded-roads overlay from the fresh geometry.
    import capital_roads_link
    capital_roads_link.link_all()

    print(f"Wrote {OUT_GEOJSON} ({len(feats)} segments)")
    print(f"Wrote {OUT_INFO}")
    print(f"  Burton rated miles={rated_mi} (total {total_mi}); Burton %={b_pct}")
    print(f"  Genesee(n_seg={len(genesee_raw)}) %={g_pct}")
    print(f"  busiest: {busiest_name} {busiest_adt:,}/day; rating years={dict(sorted(years.items()))}")
    print(f"  geojson size: {os.path.getsize(OUT_GEOJSON) // 1024} KiB")
    return 0


def _surface_series(burton: list) -> list:
    miles = defaultdict(float)
    for f in burton:
        a = f["properties"]
        s = (a.get("SURFTYPE") or "Other").strip() or "Other"
        if s == "Undefined":
            s = "Other"
        miles[s] += a.get("LENGTHMILE") or 0
    return [{"label": k, "value": round(v, 1)}
            for k, v in sorted(miles.items(), key=lambda kv: kv[1], reverse=True) if v >= 0.05]


def _road_table(burton: list) -> dict:
    """Aggregate federal-aid segments by road name: total miles + miles-weighted
    PASER -> Good/Fair/Poor, busiest first."""
    agg: dict[str, dict] = {}
    for f in burton:
        a = f["properties"]
        name = (a.get("PRNAME") or "Road").strip() or "Road"
        g = _group(a.get("CURRRATING"))
        mi = a.get("LENGTHMILE") or 0
        d = agg.setdefault(name, {"miles": 0.0, "rated_mi": 0.0, "wsum": 0.0, "adt": 0})
        d["miles"] += mi
        d["adt"] = max(d["adt"], a.get("AADT") or 0)
        if g:
            d["rated_mi"] += mi
            d["wsum"] += int(a.get("CURRRATING")) * mi
    rows = []
    for name in sorted(agg, key=lambda n: agg[n]["adt"], reverse=True):
        d = agg[name]
        if d["rated_mi"] > 0:
            avg = d["wsum"] / d["rated_mi"]
            cond = "Good" if avg >= 8 else "Fair" if avg >= 5 else "Poor"
        else:
            cond = "Not Rated"
        rows.append({
            "cells": [name, cond, f"{d['miles']:.2f}", f"{d['adt']:,}" if d["adt"] else "n/a"],
            "color": COND_COLOR.get(cond, COND_FALLBACK),
        })
    return {
        "title": "Federal-aid roads in Burton",
        "columns": ["Road", "Condition", "Miles", "Daily traffic"],
        "rows": rows,
    }


if __name__ == "__main__":
    sys.exit(main())
