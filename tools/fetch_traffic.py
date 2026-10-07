# Build public/traffic-aadt.geojson (map overlay) and tools/data/traffic-summary.json
# (aggregates read by tools/extract_crashes.py for the Roadway Safety panel).
#
# Counts: MDOT statewide AADT 2025 FeatureServer (state + federal-aid roads only;
# public). Segments are clipped to the city boundary (midpoint or any vertex inside).
# MDOT has no road-name field, so segments are labelled from the nearest Genesee
# County (GCMPC) traffic-count point within 150 m (names only; its counts are old).
#
# Styling/popup are baked into each feature (_color/_weight/_popupRows), the same
# convention paser-roads.geojson uses, so src/lib/map/dataLayers.ts needs no change.
#
# Re-runnable (committed output; the site never calls ArcGIS):
#     python tools/fetch_traffic.py
#
# Stdlib only (tools/lib helpers).
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from datetime import date

from lib.arcgis import paged_query
from lib.geo import round_coords
from lib.iox import write_geojson, write_json
from lib.paths import REPO_ROOT, public_path

OUT_GEOJSON = public_path("traffic-aadt.geojson")
OUT_SUMMARY = os.path.join(REPO_ROOT, "tools", "data", "traffic-summary.json")
BOUNDARY = public_path("boundary.geojson")

MDOT = ("https://gisagomdot.state.mi.us/arcgis/rest/services/MDOT/"
        "MdotAadtCaadt2025/FeatureServer/0/query")
COUNTY = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
          "Latest_Traffic_Count_AADT/FeatureServer/0/query")
BBOX = "-83.70,42.95,-83.55,43.03"
PAGE = 1000
NAME_RADIUS_M = 150.0
RATIO_MIN, RATIO_MAX = 0.4, 2.5  # county AADT / MDOT Aadt must fall in this range
FALLBACK = {"TL": "State highway segment", "LR": "Local road segment"}
MIN_SEGMENTS = 100
MIN_MILES = 20.0
M_PER_MILE = 1609.344

BANDS = ["<2k", "2k-5k", "5k-10k", "10k-20k", "20k+"]
BAND_COLOR = {"<2k": "#9ecae1", "2k-5k": "#4ea735", "5k-10k": "#e8c400",
              "10k-20k": "#e08a00", "20k+": "#c0392b"}
BAND_WEIGHT = {"<2k": 2, "2k-5k": 3, "5k-10k": 4, "10k-20k": 6, "20k+": 8}


def band_for(aadt: int) -> str:
    if aadt < 2000:
        return "<2k"
    if aadt < 5000:
        return "2k-5k"
    if aadt < 10000:
        return "5k-10k"
    if aadt < 20000:
        return "10k-20k"
    return "20k+"


def haversine_m(a, b) -> float:
    """Great-circle distance in metres between two [lon, lat] points."""
    r = 6371008.8
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def _lines(geom: dict) -> list:
    if geom.get("type") == "LineString":
        return [geom["coordinates"]]
    if geom.get("type") == "MultiLineString":
        return list(geom["coordinates"])
    return []


def length_m(geom: dict) -> float:
    return sum(haversine_m(ln[i], ln[i + 1]) for ln in _lines(geom) for i in range(len(ln) - 1))


def midpoint(geom: dict):
    """Point halfway along the path length, or None if there is no usable geometry."""
    lines = _lines(geom)
    total = length_m(geom)
    if not lines or total == 0:
        return None
    half, run = total / 2, 0.0
    for ln in lines:
        for i in range(len(ln) - 1):
            seg = haversine_m(ln[i], ln[i + 1])
            if run + seg >= half and seg > 0:
                t = (half - run) / seg
                return [ln[i][0] + t * (ln[i + 1][0] - ln[i][0]),
                        ln[i][1] + t * (ln[i + 1][1] - ln[i][1])]
            run += seg
    return lines[-1][-1]


def load_rings(path: str = BOUNDARY) -> list:
    with open(path, encoding="utf-8") as fh:
        b = json.load(fh)
    geom = b["features"][0]["geometry"] if b.get("type") == "FeatureCollection" else b.get("geometry", b)
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [ring for poly in polys for ring in poly]


def inside(lon: float, lat: float, rings: list) -> bool:
    ins = False
    for ring in rings:
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
            if ((y1 > lat) != (y2 > lat)) and (lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1):
                ins = not ins
    return ins


def in_city(geom: dict, rings: list) -> bool:
    mid = midpoint(geom)
    if mid and inside(mid[0], mid[1], rings):
        return True
    return any(inside(p[0], p[1], rings) for ln in _lines(geom) for p in ln)


def clean_name(raw: str) -> str:
    """Trim, collapse spaces, drop periods inside tokens; title-case only all-caps sources."""
    s = " ".join(str(raw or "").replace(".", "").split())
    return s.title() if s.isupper() else s


def ratio_ok(county_aadt, aadt) -> bool:
    """True when the county count is within a factor of 2.5 of the MDOT count (a crossing
    street's count fails; a same-road count passes). Unknown counts are not checked."""
    if not county_aadt or not aadt:
        return True
    return RATIO_MIN <= county_aadt / aadt <= RATIO_MAX


def nearest_name(verts: list, points: list, aadt=None, radius: float = NAME_RADIUS_M):
    """Name of the closest county point (distance to its nearest vertex, within radius
    metres) whose own AADT passes ratio_ok against aadt; the next-nearest is tried when
    the nearest fails. verts: [[lon, lat]]; points: [(lon, lat, name, county_aadt)]."""
    cands = []
    for lon, lat, name, c_aadt in points:
        d = min(haversine_m(v, [lon, lat]) for v in verts)
        if d <= radius:
            cands.append((d, name, c_aadt))
    for _d, name, c_aadt in sorted(cands, key=lambda c: c[0]):
        if ratio_ok(c_aadt, aadt):
            return name
    return None


def _int(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def build_features(raw: list, rings: list, names: list) -> list:
    out = []
    for f in raw:
        geom = f.get("geometry") or {}
        p = f.get("properties") or {}
        aadt = _int(p.get("Aadt"))
        year = _int(p.get("Year"))
        if not aadt or aadt <= 0 or not _lines(geom) or not in_city(geom, rings):
            continue
        com = _int(p.get("AadtCommercial"))
        prog = str(p.get("Program") or "").strip()
        fac = str(p.get("FacilityType") or "").strip() or None
        trucks = round(100 * com / aadt) if com is not None and com >= 0 else None
        verts = [pt for ln in _lines(geom) for pt in ln]
        name = nearest_name(verts, names, aadt)
        named = bool(name)
        if not named:
            name = FALLBACK.get(prog, "Road segment")
        band = band_for(aadt)
        rows = [["Daily vehicles", f"{aadt:,}"]]
        if trucks is not None:
            rows.append(["Trucks", f"{trucks}%"])
        if year:
            rows.append(["Count year", str(year)])
        coords = [round_coords(ln) for ln in _lines(geom)]
        g = ({"type": "LineString", "coordinates": coords[0]} if len(coords) == 1
             else {"type": "MultiLineString", "coordinates": coords})
        out.append({"type": "Feature", "geometry": g, "properties": {
            "name": name, "aadt": aadt, "trucks_pct": trucks, "year": year, "band": band,
            "length_m": int(round(length_m(geom))), "program": prog or None,
            "facility_type": fac, "_named": named,
            "_color": BAND_COLOR[band], "_weight": BAND_WEIGHT[band], "_popupRows": rows,
        }})
    return out


def summarize(features: list) -> dict:
    miles = {b: 0.0 for b in BANDS}
    for f in features:
        pr = f["properties"]
        miles[pr["band"]] += pr["length_m"] / M_PER_MILE
    named = [f["properties"] for f in features if f["properties"].get("_named")]
    busiest, seen = [], set()
    for pr in sorted(named, key=lambda x: -x["aadt"]):
        key = (pr["name"], pr["aadt"])
        if key in seen:
            continue
        seen.add(key)
        busiest.append({"name": pr["name"], "aadt": pr["aadt"],
                        "trucks_pct": pr["trucks_pct"], "year": pr["year"]})
        if len(busiest) == 5:
            break
    years = [f["properties"]["year"] for f in features if f["properties"]["year"]]
    return {
        "segments": len(features),
        "miles_by_band": {b: round(miles[b], 1) for b in BANDS},
        "busiest": busiest,
        "median_aadt": int(statistics.median(f["properties"]["aadt"] for f in features)),
        "years": {"min": min(years), "max": max(years)} if years else {"min": None, "max": None},
        "extracted": date.today().isoformat(),
        "_source": "MDOT statewide AADT 2025 (state and federal-aid roads); road names from "
                   "Genesee County Metropolitan Planning Commission traffic-count points",
    }


def check_guards(features: list, summary: dict) -> None:
    if len(features) < MIN_SEGMENTS:
        raise SystemExit(f"guard: only {len(features)} segments after clipping (need >= {MIN_SEGMENTS})")
    total = sum(summary["miles_by_band"].values())
    if total < MIN_MILES:
        raise SystemExit(f"guard: only {total:.1f} miles across bands (need >= {MIN_MILES})")


def fetch_mdot() -> list:
    params = {"where": "1=1", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
              "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
              "outFields": "PR,FacilityType,Program,Aadt,AadtCommercial,Year",
              "outSR": "4326", "f": "geojson"}
    return list(paged_query(MDOT, params, page_size=PAGE, timeout=120))


def fetch_names() -> list:
    params = {"where": "ON_ROAD IS NOT NULL", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
              "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
              "outFields": "ON_ROAD,AADT", "outSR": "4326", "f": "geojson"}
    pts = []
    for f in paged_query(COUNTY, params, page_size=1000, timeout=120):
        g = f.get("geometry") or {}
        props = f.get("properties") or {}
        nm = (props.get("ON_ROAD") or "").strip()
        if g.get("type") == "Point" and nm:
            pts.append((g["coordinates"][0], g["coordinates"][1], clean_name(nm),
                        _int(props.get("AADT"))))
    return pts


def main() -> int:
    raw = fetch_mdot()
    names = fetch_names()
    rings = load_rings()
    feats = build_features(raw, rings, names)
    if not feats:
        raise SystemExit("guard: no segments after clipping")
    summary = summarize(feats)
    check_guards(feats, summary)
    n_named = sum(1 for f in feats if f["properties"]["_named"])
    for f in feats:
        del f["properties"]["_named"]
    write_geojson(OUT_GEOJSON, {"type": "FeatureCollection", "features": feats})
    write_json(OUT_SUMMARY, summary)
    kb = os.path.getsize(OUT_GEOJSON) / 1024
    print(f"MDOT segments fetched: {len(raw)}; county name points: {len(names)}")
    print(f"Kept after clipping: {len(feats)}; named: {n_named}; unnamed: {len(feats) - n_named}")
    print(f"Miles by band: {summary['miles_by_band']}")
    print(f"Guards passed (>= {MIN_SEGMENTS} segments, >= {MIN_MILES} miles); "
          f"median AADT {summary['median_aadt']}; busiest {summary['busiest'][:2]}")
    print(f"Wrote {OUT_GEOJSON} ({kb:.0f} KB) and {OUT_SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
