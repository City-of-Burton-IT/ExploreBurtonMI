"""Build the "Sites for Business" overlays and dashboard (ADR-0003 Part C).

Two parcel-level overlays from the Assessing roll, approved 2026-10-15:

  public/business-sites-vacant.geojson    classes 202 (vacant commercial) and
                                          302 (vacant industrial): land to build on
  public/business-sites-improved.geojson  classes 201 and 301: existing commercial
                                          and industrial buildings (an inventory;
                                          the roll does not know what is for lease)

plus public/info-businesssites.json, the dashboard, which carries ONE citywide
line about commercial transfers (a count, no prices; see the ADR for why
commercial prices are never aggregated by neighbourhood).

PUBLISHED PER PARCEL: parcel number, situs address, class, acres, frontage,
zoning, coordinates. NEVER: owner, value, tax status, sale history. The source
CSV has none of those columns, so the tool cannot leak them.

SOURCE: pipeline/data/commercial-parcels.csv and commercial-sales-summary.json
from tools/Export-BsaCommercialParcels.ps1 (both gitignored). Coordinates come
from the shared Census batch path and cache (build_address_points.py), clipped
to the city boundary.

Re-runnable (committed outputs; the site reads the files, never the geocoder):
    pipeline/.venv/Scripts/python tools/build_business_sites.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter
from datetime import date

import build_address_points as bap
from lib.iox import write_geojson, write_json
from lib.paths import pipeline_data_path, public_path

SOURCE_CSV = pipeline_data_path("commercial-parcels.csv")
SOURCE_SUMMARY = pipeline_data_path("commercial-sales-summary.json")
# Optional: parcel centroids (parcel, lat, lng) from a county/City parcel GIS export.
# Most vacant lots have no street number, so the address geocoder cannot place them;
# a centroid file, when present, is used first and the geocoder only fills the rest.
CENTROIDS_CSV = pipeline_data_path("parcel-centroids.csv")
# Optional parcel outlines ({parcel: [[lng, lat], ...]}) from the same extractor; when
# present the VACANT layer draws lot outlines instead of pins (buildings stay pins).
POLYGONS_JSON = pipeline_data_path("parcel-polygons.json")
OUT_VACANT = public_path("business-sites-vacant.geojson")
OUT_IMPROVED = public_path("business-sites-improved.geojson")
OUT_INFO = public_path("info-businesssites.json")
TRAFFIC = public_path("traffic-aadt.geojson")
TRAFFIC_MAX_M = 150.0   # a site counts as "on" a counted road within this distance

REQUIRED = ["parcel", "street", "propclass", "acres", "frontage", "zoning"]
CLASSES = {
    "202": {"label": "Vacant commercial land", "vacant": True, "color": "#2e7d32"},
    "302": {"label": "Vacant industrial land", "vacant": True, "color": "#6a1b9a"},
    "201": {"label": "Commercial building", "vacant": False, "color": "#1565c0"},
    "301": {"label": "Industrial building", "vacant": False, "color": "#4e342e"},
}
BSA_ONLINE = "https://bsaonline.com/?uid=209"
TOP_SITES = 30


def _norm(s) -> str:
    return " ".join(str(s or "").split()).strip()


def read_rows(path: str = SOURCE_CSV) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"Source not found: {path}\nRun tools/Export-BsaCommercialParcels.ps1 first.")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise SystemExit(f"commercial-parcels: missing columns {missing}")
        raw = list(reader)
    if not raw:
        raise SystemExit("commercial-parcels: no rows")
    rows = []
    seen: set[str] = set()
    for i, r in enumerate(raw, start=2):
        cls = _norm(r["propclass"])
        if cls not in CLASSES:
            continue
        parcel = _norm(r["parcel"])
        if parcel in seen:
            raise SystemExit(f"commercial-parcels: parcel {parcel} appears twice (row {i})")
        seen.add(parcel)
        try:
            acres = round(float(r["acres"] or 0), 2)
            frontage = int(float(r["frontage"] or 0))
        except ValueError as exc:
            raise SystemExit(f"commercial-parcels: row {i} has a bad number: {exc}") from exc
        rows.append({
            "parcel": parcel,
            "street": _norm(r["street"]),
            "city": _norm(r.get("city")) or bap.DEFAULT_CITY,
            "zip": _norm(r.get("zip")),
            "propclass": cls,
            "acres": acres,
            "frontage": frontage,
            "zoning": _norm(r["zoning"]),
            "lat": None,
            "lng": None,
        })
    return rows


def read_summary(path: str = SOURCE_SUMMARY) -> dict:
    with open(path, encoding="utf-8") as fh:
        s = json.load(fh)
    if not isinstance(s.get("transfers24"), int) or not s.get("asOf"):
        raise SystemExit("commercial-sales-summary.json: expected {transfers24: int, asOf: date}")
    return s


def read_centroids(path: str = CENTROIDS_CSV) -> dict[str, tuple[float, float]]:
    """{parcel: (lat, lng)} from the optional centroid file; empty when absent."""
    if not os.path.exists(path):
        return {}
    out: dict[str, tuple[float, float]] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for c in ("parcel", "lat", "lng"):
            if c not in (reader.fieldnames or []):
                raise SystemExit(f"parcel-centroids: missing column {c}")
        for r in reader:
            try:
                out[_norm(r["parcel"])] = (float(r["lat"]), float(r["lng"]))
            except ValueError as exc:
                raise SystemExit(f"parcel-centroids: bad coordinate for {r.get('parcel')}: {exc}") from exc
    return out


def read_polygons(path: str = POLYGONS_JSON) -> dict[str, list]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def apply_centroids(rows: list[dict], centroids: dict[str, tuple[float, float]]) -> int:
    """Set lat/lng from the centroid file where a parcel matches. Returns the count."""
    n = 0
    for r in rows:
        c = centroids.get(r["parcel"])
        if c:
            r["lat"], r["lng"] = c
            n += 1
    return n


def geocode(rows: list[dict]) -> None:
    for i, r in enumerate(rows):
        r.update({"id": str(i), "state": bap.DEFAULT_STATE})
    cache = bap._load_cache()
    bap.geocode_batch([r for r in rows if r["street"] and r["lat"] is None], cache)


def load_traffic(path: str = TRAFFIC) -> list[dict]:
    """Counted road segments as {name, aadt, year, coords[[lng,lat],...]}; empty if absent."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        fc = json.load(fh)
    out = []
    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        p = f.get("properties") or {}
        if g.get("type") != "LineString" or not p.get("aadt"):
            continue
        out.append({"name": p.get("name") or "counted road", "aadt": int(p["aadt"]),
                    "year": p.get("year"), "coords": g["coordinates"]})
    return out


def _seg_distance_m(lng: float, lat: float, a: list, b: list) -> float:
    """Planar point-to-segment distance in metres (fine at city scale)."""
    kx = 111_320.0 * math.cos(math.radians(lat))
    ky = 110_540.0
    px, py = lng * kx, lat * ky
    ax, ay = a[0] * kx, a[1] * ky
    bx, by = b[0] * kx, b[1] * ky
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def nearest_traffic(lng: float, lat: float, segments: list[dict], max_m: float = TRAFFIC_MAX_M) -> dict | None:
    """The busiest counted segment within max_m of the point, or None."""
    best = None
    for seg in segments:
        c = seg["coords"]
        d = min(_seg_distance_m(lng, lat, c[i], c[i + 1]) for i in range(len(c) - 1))
        if d <= max_m and (best is None or seg["aadt"] > best["aadt"]):
            best = seg
    return best


def popup_rows(r: dict) -> list[list[str]]:
    rows = [["Type", CLASSES[r["propclass"]]["label"]]]
    if r["acres"] > 0:
        rows.append(["Lot size", f"{r['acres']:g} acres"])
    if r["frontage"] > 0:
        rows.append(["Frontage", f"{r['frontage']:,} ft"])
    if r["zoning"]:
        rows.append(["Zoning", r["zoning"]])
    t = r.get("traffic")
    if t:
        rows.append(["Traffic on nearest counted road",
                     f"{t['aadt']:,} vehicles a day ({t['name']}, {t['year']})"])
    rows.append(["Parcel", r["parcel"]])
    rows.append(["Details", "Look up the parcel on BS&A Online (link on the dashboard)"])
    return rows


def _feature(r: dict, ring: list | None = None) -> dict:
    meta = CLASSES[r["propclass"]]
    radius = 7 if meta["vacant"] else 5
    if r["acres"] >= 5:
        radius += 3
    elif r["acres"] >= 1:
        radius += 1
    if ring:
        geometry = {"type": "Polygon", "coordinates": [ring]}
        style = {"_weight": 2, "_fillOpacity": 0.45}
    else:
        geometry = {"type": "Point", "coordinates": [round(r["lng"], 6), round(r["lat"], 6)]}
        style = {"_radius": radius}
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "name": bap.titlecase_street(r["street"]) or f"Parcel {r['parcel']}",
            "parcel": r["parcel"],
            "propclass": r["propclass"],
            "acres": r["acres"],
            "zoning": r["zoning"],
            "_color": meta["color"],
            **style,
            "_popupRows": popup_rows(r),
        },
    }


def build_layers(rows: list[dict], rings: list[list],
                 traffic: list[dict] | None = None,
                 polygons: dict[str, list] | None = None) -> tuple[dict, dict, int, int]:
    """(vacant_fc, improved_fc, n_nocoord, n_outside)."""
    vacant, improved = [], []
    nocoord = outside = 0
    for r in rows:
        if r["lat"] is None or r["lng"] is None:
            nocoord += 1
            continue
        if not bap.in_city(r["lng"], r["lat"], rings):
            outside += 1
            continue
        if traffic:
            r["traffic"] = nearest_traffic(r["lng"], r["lat"], traffic)
        if CLASSES[r["propclass"]]["vacant"]:
            vacant.append(_feature(r, (polygons or {}).get(r["parcel"])))
        else:
            improved.append(_feature(r))
    for feats in (vacant, improved):
        feats.sort(key=lambda f: (-f["properties"]["acres"], f["properties"]["name"]))
    return ({"type": "FeatureCollection", "features": vacant},
            {"type": "FeatureCollection", "features": improved}, nocoord, outside)


def build_panel(rows: list[dict], summary: dict, nocoord: int, outside: int, today: date) -> dict:
    by_class = {c: [r for r in rows if r["propclass"] == c] for c in CLASSES}
    acres = {c: round(sum(r["acres"] for r in v)) for c, v in by_class.items()}
    vacant_rows = by_class["202"] + by_class["302"]

    stats = [
        {"label": "Vacant commercial parcels", "value": f"{len(by_class['202']):,}",
         "hint": f"{acres['202']:,} acres"},
        {"label": "Vacant industrial parcels", "value": f"{len(by_class['302']):,}",
         "hint": f"{acres['302']:,} acres"},
        {"label": "Commercial buildings", "value": f"{len(by_class['201']):,}",
         "hint": f"{acres['201']:,} acres of improved commercial land"},
        {"label": "Industrial buildings", "value": f"{len(by_class['301']):,}",
         "hint": f"{acres['301']:,} acres of improved industrial land"},
        {"label": "Commercial and industrial buildings sold, last 24 months",
         "value": f"{summary['transfers24']:,}",
         "hint": "arms-length sales recorded by the Assessor; count only"},
    ]

    charts = [
        {"type": "bars", "title": "Acres by property class",
         "series": [{"label": CLASSES[c]["label"], "value": acres[c], "color": CLASSES[c]["color"]}
                    for c in ("202", "302", "201", "301")]},
    ]
    zoning_counts = Counter(r["zoning"] or "Not coded" for r in vacant_rows).most_common(8)
    if zoning_counts:
        charts.append({"type": "bars", "title": "Vacant sites by zoning district",
                       "series": [{"label": z, "value": n} for z, n in zoning_counts]})

    top = sorted(vacant_rows, key=lambda r: -r["acres"])[:TOP_SITES]
    tables = [{
        "title": f"Largest vacant commercial and industrial sites (top {len(top)} by acreage)",
        "columns": ["Address", "Type", "Acres", "Frontage (ft)", "Zoning"],
        "rows": [{"cells": [
            bap.titlecase_street(r["street"]) or f"Parcel {r['parcel']}",
            "Commercial" if r["propclass"] == "202" else "Industrial",
            f"{r['acres']:g}", f"{r['frontage']:,}" if r["frontage"] else "n/a", r["zoning"] or "n/a",
        ], "color": CLASSES[r["propclass"]]["color"]} for r in top],
    }]

    notes = [
        "Turn on the \"Vacant commercial and industrial sites\" overlay to see land to build on, drawn as lot outlines from the City parcel map, and \"Commercial and industrial buildings\" for the existing stock as dots.",
        "The City's Assessing roll classifies every parcel; a vacant commercial or industrial parcel is one with no building on it. The roll does not record whether a parcel or building is for sale or lease, so contact the owner through BS&A Online or a broker.",
        "Each listing shows the parcel number, address, lot size, frontage and zoning. Owner names, assessed values and tax status are not shown here; those are available per parcel on BS&A Online.",
        "Where a site sits within about 150 m of a road with an MDOT traffic count, its popup shows the daily vehicle count from the Traffic volume overlay.",
        f"{nocoord + outside} parcels could not be placed on the map (no geocodable address) and appear only in the counts.",
    ]
    return {
        "title": "Sites for Business",
        "subtitle": "Vacant commercial and industrial land, and the existing building stock, from the City Assessor's roll",
        "lastUpdated": today.isoformat(),
        "stats": stats,
        "charts": charts,
        "tables": tables,
        "source": f"City of Burton Assessor property roll (BS&A), property classes 201, 202, 301 and 302. Transfer count from Assessor sales records as of {summary['asOf']}.",
        "links": [
            {"text": "Look up a parcel on BS&A Online", "href": BSA_ONLINE},
            {"text": "Burton zoning information", "href": "https://www.burtonmi.gov/departments/department_of_public_works/zoning_division.php"},
            {"text": "Burton Assessor's Office", "href": "https://www.burtonmi.gov/government/assessor2/index.php"},
        ],
        "notes": notes,
    }


def main() -> int:
    today = date.today()
    rows = read_rows()
    summary = read_summary()
    print(f"Read {len(rows)} commercial/industrial parcels from {os.path.basename(SOURCE_CSV)}")
    placed = apply_centroids(rows, read_centroids())
    print(f"  {placed} placed from parcel-centroids.csv" if placed else
          "  no parcel-centroids.csv: vacant lots without a street number cannot be geocoded")
    geocode(rows)
    rings = bap._rings_from_boundary()
    traffic = load_traffic()
    polygons = read_polygons()
    vacant, improved, nocoord, outside = build_layers(rows, rings, traffic, polygons)
    outlines = sum(1 for f in vacant["features"] if f["geometry"]["type"] == "Polygon")
    print(f"  {outlines} vacant sites drawn as lot outlines" if polygons else "  no parcel-polygons.json: vacant sites drawn as pins")
    with_traffic = sum(1 for fc in (vacant, improved) for f in fc["features"]
                       if any(k == "Traffic on nearest counted road" for k, _ in f["properties"]["_popupRows"]))
    print(f"  {with_traffic} sites within {TRAFFIC_MAX_M:.0f} m of a counted road ({len(traffic)} segments)")
    write_geojson(OUT_VACANT, vacant)
    write_geojson(OUT_IMPROVED, improved)
    write_json(OUT_INFO, build_panel(rows, summary, nocoord, outside, today))
    print(f"Wrote {len(vacant['features'])} vacant sites and {len(improved['features'])} buildings "
          f"(dropped {nocoord} un-geocoded, {outside} outside city); transfers24={summary['transfers24']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
