# Build public/traffic-aadt.geojson (map overlay) and tools/data/traffic-summary.json
# (aggregates read by tools/extract_crashes.py for the Roadway Safety panel).
#
# Counts: MDOT statewide AADT FeatureServer, one layer per year (state + federal-aid
# roads only; public). Segments are clipped to the city boundary (midpoint or any
# vertex inside). MDOT has no road-name field, so each segment is named from, in order:
#   1. the nearest named road line within 40 m whose bearing matches (within 30 deg):
#      OpenStreetMap named highways fetched from Overpass (ODbL; freeways use the
#      route ref, so I-69 and I-475 read as such) and the committed PASER lines in
#      public/paser-roads.geojson (RoadSoft names for county roads and the I-69 ramps);
#   2. the nearest Genesee County (GCMPC) traffic-count point within 150 m whose own
#      count is within a factor of 2.5 of the MDOT count (its counts are old; names only).
# Lines come first because count points sit at intersections and name the crossing
# street about one time in ten; a parallel line within 40 m with the same bearing does not.
#
# Styling/popup are baked into each feature (_color/_weight/_popupRows), the same
# convention paser-roads.geojson uses, so src/lib/map/dataLayers.ts needs no change.
#
# Re-runnable (committed output; the site never calls ArcGIS or Overpass):
#     python tools/fetch_traffic.py [--year 2025]
# After a year change also update the heading in public/dashboard-clarity.json
# ("Traffic volume (MDOT <year>)"); tools/extract_crashes.py reads the year from the
# summary file.
#
# Stdlib only (tools/lib helpers).
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from datetime import date

from lib.arcgis import paged_query
from lib.geo import round_coords
from lib.httpio import get_json
from lib.iox import write_geojson, write_json
from lib.paths import REPO_ROOT, public_path

OUT_GEOJSON = public_path("traffic-aadt.geojson")
OUT_SUMMARY = os.path.join(REPO_ROOT, "tools", "data", "traffic-summary.json")
BOUNDARY = public_path("boundary.geojson")
PASER_ROADS = public_path("paser-roads.geojson")

DEFAULT_YEAR = 2025
MDOT_LAYER = ("https://gisagomdot.state.mi.us/arcgis/rest/services/MDOT/"
              "MdotAadtCaadt{year}/FeatureServer/0/query")
COUNTY = ("https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services/"
          "Latest_Traffic_Count_AADT/FeatureServer/0/query")
OVERPASS = "https://overpass-api.de/api/interpreter"
OSM_USER_AGENT = "ExploreBurtonMI-tools/1.0 (City of Burton IT)"
BBOX = "-83.70,42.95,-83.55,43.03"
OSM_BBOX = "42.95,-83.70,43.04,-83.55"  # Overpass order: south,west,north,east
PAGE = 1000
NAME_RADIUS_M = 150.0
LINE_RADIUS_M = 40.0
BEARING_TOL_DEG = 30.0
RATIO_MIN, RATIO_MAX = 0.4, 2.5  # county AADT / MDOT Aadt must fall in this range
FREEWAY_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link"}
M_PER_DEG = 111320.0
COS_LAT = math.cos(math.radians(43.0))  # Burton; a flat local projection is fine at 40 m
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


def _xy(p) -> tuple:
    return (p[0] * M_PER_DEG * COS_LAT, p[1] * M_PER_DEG)


def seg_dist_m(p, a, b) -> float:
    """Distance in metres from point p to the straight segment a-b (local flat projection)."""
    px, py = _xy(p)
    ax, ay = _xy(a)
    bx, by = _xy(b)
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def bearing_deg(a, b) -> float:
    """Axis bearing of a-b in [0, 180): direction of travel is irrelevant for a road."""
    ax, ay = _xy(a)
    bx, by = _xy(b)
    return (math.degrees(math.atan2(bx - ax, by - ay)) + 360.0) % 180.0


def bearing_diff(x: float, y: float) -> float:
    d = abs(x - y) % 180.0
    return min(d, 180.0 - d)


def mid_bearing(geom: dict):
    """(midpoint, axis bearing of the sub-segment holding it), or (None, None)."""
    lines = _lines(geom)
    segs = [(ln[i], ln[i + 1]) for ln in lines for i in range(len(ln) - 1)]
    total = sum(haversine_m(a, b) for a, b in segs)
    if not segs or total == 0:
        return None, None
    half, run = total / 2, 0.0
    for a, b in segs:
        d = haversine_m(a, b)
        if run + d >= half and d > 0:
            t = (half - run) / d
            return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])], bearing_deg(a, b)
        run += d
    a, b = segs[-1]
    return b, bearing_deg(a, b)


def nearest_line_name(geom: dict, lines: list, radius: float = LINE_RADIUS_M,
                      tol: float = BEARING_TOL_DEG):
    """Name of the closest road line to the segment's midpoint, within radius metres,
    whose sub-segment there runs within tol degrees of the segment's own bearing.
    lines: [(name, [[lon, lat], ...])]. A crossing street fails the bearing test."""
    pt, brg = mid_bearing(geom)
    if pt is None or brg is None:
        return None
    best = None
    for name, coords in lines:
        for i in range(len(coords) - 1):
            d = seg_dist_m(pt, coords[i], coords[i + 1])
            if d <= radius and bearing_diff(brg, bearing_deg(coords[i], coords[i + 1])) <= tol:
                if best is None or d < best[0]:
                    best = (d, name)
    return best[1] if best else None


def tidy_paser_name(raw) -> str:
    """RoadSoft names: 'E I 69' -> 'I-69', 'Belsay/E I 69 RAMP' -> 'Belsay / I-69 ramp';
    ordinary street names ('S Belsay Rd') pass through unchanged."""
    s = " ".join(str(raw or "").split())
    s = re.sub(r"\b[NSEW] I (\d+)\b", r"I-\1", s)
    s = re.sub(r"\bI (\d+)\b", r"I-\1", s)
    s = re.sub(r"\s*/\s*", " / ", s)
    return re.sub(r"\bRAMP\b", "ramp", s)


def osm_display_name(tags: dict):
    """Freeways read as their route ref ('I 69' -> 'I-69'); everything else uses name."""
    cls = tags.get("highway") or ""
    ref = (tags.get("ref") or "").split(";")[0].strip()
    name = " ".join((tags.get("name") or "").split())
    if cls in FREEWAY_CLASSES and ref:
        return re.sub(r"^I ?(\d+)$", r"I-\1", ref)
    return name or None


def osm_lines(elements: list) -> list:
    """[(display name, [[lon, lat], ...])] from Overpass 'out geom' way elements."""
    out = []
    for el in elements or []:
        if el.get("type") != "way" or not el.get("geometry"):
            continue
        name = osm_display_name(el.get("tags") or {})
        if name:
            out.append((name, [[g["lon"], g["lat"]] for g in el["geometry"]]))
    return out


def paser_lines(path: str = PASER_ROADS) -> list:
    """[(tidied name, coords)] from the committed PASER overlay; [] when it is absent."""
    if not os.path.exists(path):
        return []
    gj = json.load(open(path, encoding="utf-8"))
    out = []
    for f in gj.get("features", []):
        name = tidy_paser_name((f.get("properties") or {}).get("name"))
        for ln in _lines(f.get("geometry") or {}):
            if name:
                out.append((name, ln))
    return out


def _int(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def build_features(raw: list, rings: list, names: list,
                   line_sources: list | None = None) -> list:
    """names: county count points (fallback). line_sources: lists of named road lines
    tried in order (PASER before OSM, so a county road keeps one spelling end to end)."""
    sources = [s for s in (line_sources or []) if s]
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
        name = None
        for src in sources:
            name = nearest_line_name(geom, src)
            if name:
                break
        if not name:
            verts = [pt for ln in _lines(geom) for pt in ln]
            name = nearest_name(verts, names, aadt)
        named = bool(name)
        if not named:
            name = FALLBACK.get(prog, "Road segment")
        elif prog == "RMP" and "ramp" not in name.lower():
            name = f"{name} ramp"  # matched the mainline rather than a named ramp
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


def summarize(features: list, year: int = DEFAULT_YEAR) -> dict:
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
        "mdot_year": year,
        "_source": f"MDOT statewide AADT {year} (state and federal-aid roads); road names from "
                   "OpenStreetMap (ODbL, (c) OpenStreetMap contributors) and Genesee County "
                   "RoadSoft/PASER lines, with Genesee County Metropolitan Planning Commission "
                   "traffic-count points as the fallback",
    }


def check_guards(features: list, summary: dict) -> None:
    if len(features) < MIN_SEGMENTS:
        raise SystemExit(f"guard: only {len(features)} segments after clipping (need >= {MIN_SEGMENTS})")
    total = sum(summary["miles_by_band"].values())
    if total < MIN_MILES:
        raise SystemExit(f"guard: only {total:.1f} miles across bands (need >= {MIN_MILES})")


def mdot_url(year: int) -> str:
    return MDOT_LAYER.format(year=int(year))


def fetch_mdot(year: int = DEFAULT_YEAR) -> list:
    params = {"where": "1=1", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
              "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
              "outFields": "PR,FacilityType,Program,Aadt,AadtCommercial,Year",
              "outSR": "4326", "f": "geojson"}
    return list(paged_query(mdot_url(year), params, page_size=PAGE, timeout=120))


def fetch_osm_roads() -> list:
    """Named OSM highways in the bbox as road lines (freeways carry a name and a ref).
    Overpass answers 406 to a generic browser User-Agent, so a project one is sent."""
    query = f'[out:json][timeout:90];way["highway"]["name"]({OSM_BBOX});out geom;'
    data = get_json(OVERPASS, {"data": query}, timeout=120,
                    headers={"User-Agent": OSM_USER_AGENT})
    return osm_lines(data.get("elements", []))


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


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build the MDOT traffic-volume overlay and summary.")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR,
                    help=f"MDOT AADT layer year, MdotAadtCaadt<year> (default {DEFAULT_YEAR})")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    raw = fetch_mdot(args.year)
    names = fetch_names()
    paser, osm = paser_lines(), fetch_osm_roads()
    rings = load_rings()
    feats = build_features(raw, rings, names, [paser, osm])
    if not feats:
        raise SystemExit("guard: no segments after clipping")
    summary = summarize(feats, args.year)
    check_guards(feats, summary)
    n_named = sum(1 for f in feats if f["properties"]["_named"])
    for f in feats:
        del f["properties"]["_named"]
    write_geojson(OUT_GEOJSON, {"type": "FeatureCollection", "features": feats})
    write_json(OUT_SUMMARY, summary)
    kb = os.path.getsize(OUT_GEOJSON) / 1024
    print(f"MDOT {args.year} segments fetched: {len(raw)}; county name points: {len(names)}; "
          f"named road lines: PASER {len(paser)}, OSM {len(osm)}")
    print(f"Kept after clipping: {len(feats)}; named: {n_named}; unnamed: {len(feats) - n_named}")
    print(f"Miles by band: {summary['miles_by_band']}")
    print(f"Guards passed (>= {MIN_SEGMENTS} segments, >= {MIN_MILES} miles); "
          f"median AADT {summary['median_aadt']}; busiest {summary['busiest'][:2]}")
    print(f"Wrote {OUT_GEOJSON} ({kb:.0f} KB) and {OUT_SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
