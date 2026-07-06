# Build public/transit-routes.geojson: the MTA Flint bus routes that serve the
# City of Burton, as a map overlay layer (route lines colored by the agency's own
# route colors).
#
# Source: MTA Flint GTFS static feed (https://www.mtaflint.org/wp-content/media/gtfs.zip).
# MTA's Terms of Use ("you may use MTA content displayed on the Site"; maps/schedules
# are named MTA content) cover displaying this public-service route information. Routes
# are stable, so the committed output is what the site reads (refresh occasionally).
#
# Re-runnable:
#     python tools/extract_transit.py [--gtfs <path-to-gtfs.zip-or-dir>]
#
# Which routes "serve Burton" is derived from public/boundary.geojson each run (a route
# is included if its path passes through the city), not hard-coded.
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile

GTFS_URL = "https://www.mtaflint.org/wp-content/media/gtfs.zip"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
OUT = os.path.join(ROOT, "public", "transit-routes.geojson")
OUT_STOPS = os.path.join(ROOT, "public", "bus-stops.geojson")
DEFAULT_COLOR = "1f6fb2"
STOP_COLOR = "#1f6fb2"


def _rings(geom: dict) -> list:
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def _pip(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _load_boundary():
    boundary = json.load(open(BOUNDARY, encoding="utf-8"))
    rings = _rings(boundary)
    xs = [p[0] for poly in rings for ring in poly for p in ring]
    ys = [p[1] for poly in rings for ring in poly for p in ring]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    return rings, bbox


def _in_burton(lon: float, lat: float, rings: list, bbox: tuple) -> bool:
    if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
        return False
    return any(_pip(lon, lat, poly[0]) for poly in rings)


def _read_gtfs(path: str | None) -> dict[str, list[dict]]:
    """Return {table: list-of-row-dicts} for the GTFS tables we need."""
    want = ("routes", "trips", "shapes", "stops")
    if path and os.path.isdir(path):
        blobs = {t: open(os.path.join(path, f"{t}.txt"), encoding="utf-8-sig").read() for t in want}
    else:
        if path:
            data = open(path, "rb").read()
        else:
            print(f"Downloading {GTFS_URL} ...")
            req = urllib.request.Request(GTFS_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
        zf = zipfile.ZipFile(io.BytesIO(data))
        blobs = {t: zf.read(f"{t}.txt").decode("utf-8-sig") for t in want}
    return {t: list(csv.DictReader(io.StringIO(b))) for t, b in blobs.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Burton bus-routes overlay from MTA GTFS.")
    parser.add_argument("--gtfs", help="Path to gtfs.zip or an extracted GTFS dir (default: download)")
    args = parser.parse_args()

    rings, bbox = _load_boundary()
    gtfs = _read_gtfs(args.gtfs)

    routes = {r["route_id"]: r for r in gtfs["routes"]}

    # shape_id -> ordered list of [lon, lat]
    shapes: dict[str, list] = {}
    for row in sorted(gtfs["shapes"], key=lambda r: (r["shape_id"], int(r["shape_pt_sequence"]))):
        shapes.setdefault(row["shape_id"], []).append(
            [round(float(row["shape_pt_lon"]), 5), round(float(row["shape_pt_lat"]), 5)]
        )

    # route_id -> set of shape_ids actually used by its trips
    route_shapes: dict[str, set] = {}
    for t in gtfs["trips"]:
        sid = t.get("shape_id")
        if sid:
            route_shapes.setdefault(t["route_id"], set()).add(sid)

    features = []
    for route_id, shape_ids in route_shapes.items():
        # pick the route's longest shape as its representative line
        best = max((shapes.get(s, []) for s in shape_ids), key=len, default=[])
        if len(best) < 2:
            continue
        if not any(_in_burton(lon, lat, rings, bbox) for lon, lat in best):
            continue  # this route does not pass through Burton
        r = routes.get(route_id, {})
        short = (r.get("route_short_name") or route_id).strip()
        long = (r.get("route_long_name") or "").strip()
        name = f"Route {short} - {long}" if long else f"Route {short}"
        color = (r.get("route_color") or "").strip() or DEFAULT_COLOR
        feat = {
            "type": "Feature",
            "properties": {
                "name": name,
                "route": short,
                "_color": f"#{color}",
            },
            "geometry": {"type": "LineString", "coordinates": best},
        }
        url = (r.get("route_url") or "").strip()
        if url:
            feat["properties"]["url"] = url
        features.append(feat)

    if not features:
        raise SystemExit("No MTA routes through Burton parsed from the GTFS feed (schema change?).")

    features.sort(key=lambda f: (len(f["properties"]["route"]), f["properties"]["route"]))
    fc = {
        "type": "FeatureCollection",
        "_source": (
            "MTA Flint GTFS static feed (mtaflint.org). Routes whose path passes through the City "
            "of Burton; line colors are the agency's published route colors."
        ),
        "features": features,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  {len(features)} MTA routes through Burton:")
    for f in features:
        print(f"    {f['properties']['name']}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")

    # Bus stops inside Burton (GTFS stops.txt) as a point overlay, the rider-facing
    # stop list (the county ArcGIS stop layers have no usable stop names).
    stops_feats = []
    for s in gtfs.get("stops", []):
        try:
            lon = float(s["stop_lon"])
            lat = float(s["stop_lat"])
        except (KeyError, ValueError, TypeError):
            continue
        if not _in_burton(lon, lat, rings, bbox):
            continue
        name = (s.get("stop_name") or "Bus stop").strip()
        stops_feats.append({
            "type": "Feature",
            "properties": {"name": name, "_color": STOP_COLOR},
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
        })
    if not stops_feats:
        raise SystemExit("No MTA bus stops inside Burton parsed from the GTFS feed (schema change?).")

    stops_feats.sort(key=lambda f: f["properties"]["name"])
    stops_fc = {
        "type": "FeatureCollection",
        "_source": "MTA Flint GTFS bus stops within the City of Burton.",
        "features": stops_feats,
    }
    with open(OUT_STOPS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(stops_fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"Wrote {OUT_STOPS} ({len(stops_feats)} bus stops in Burton)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
