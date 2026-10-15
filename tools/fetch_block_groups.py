"""Build public/block-groups.geojson: the Census block groups that cover Burton,
the spatial unit for the Home Sale Prices tiles (ADR-0003 Part B).

Source: Census TIGERweb (public domain), current block groups, queried by the
city's bounding box. A block group is kept when at least MIN_ADDRESSES City situs address
points (public/address-points.json) fall inside it, which trims the bbox pull to
the groups that actually hold Burton homes. Polygons are kept whole (the map's
dim mask hides the out-of-city parts); coordinates are rounded to ~1 m.

Re-runnable (committed output; the site reads the file, never TIGERweb):
    pipeline/.venv/Scripts/python tools/fetch_block_groups.py

Refresh when the Census publishes a new block-group vintage (decennially) or when
the address roll changes materially.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

from lib.geo import round_coords
from lib.iox import write_geojson
from lib.paths import public_path

BOUNDARY = public_path("boundary.geojson")
ADDRESS_POINTS = public_path("address-points.json")
OUT = public_path("block-groups.geojson")
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/1/query"
USER_AGENT = "ExploreBurtonMI/1.0 (tools/fetch_block_groups.py)"
# A block group on the city edge can catch one or two Burton addresses; such a
# sliver would never reach the five-sale floor and only clutters the overlay.
MIN_ADDRESSES = 10


def _walk(coords, acc: list) -> None:
    if isinstance(coords[0], (int, float)):
        acc.append(coords)
    else:
        for c in coords:
            _walk(c, acc)


def bbox_of(geojson: dict) -> tuple[float, float, float, float]:
    feats = geojson["features"] if geojson.get("type") == "FeatureCollection" else [geojson]
    pts: list = []
    for f in feats:
        _walk((f.get("geometry") or f)["coordinates"], pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def fetch(bbox: tuple[float, float, float, float]) -> dict:
    params = {
        "geometry": ",".join(str(v) for v in bbox),
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "GEOID,STATE,COUNTY,TRACT,BLKGRP",
        "outSR": 4326,
        "f": "geojson",
    }
    req = urllib.request.Request(TIGERWEB + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        gj = json.load(resp)
    if gj.get("error") or not gj.get("features"):
        raise SystemExit(f"TIGERweb query failed: {gj.get('error') or 'no features'}")
    return gj


def rings_of(geom: dict) -> list[list]:
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def _in_ring(lng: float, lat: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(rings: list[list], lng: float, lat: float) -> bool:
    return any(_in_ring(lng, lat, r) for r in rings)


def select_block_groups(tiger: dict, address_points: list[list], min_addresses: int = MIN_ADDRESSES) -> dict:
    """Keep the block groups holding at least min_addresses city address points;
    rebuild the feature with the small property set the site needs."""
    features = []
    for f in tiger["features"]:
        rings = rings_of(f["geometry"])
        n = sum(1 for lat, lng, *_ in address_points if contains(rings, lng, lat))
        if n < min_addresses:
            continue
        p = f["properties"]
        features.append({
            "type": "Feature",
            "geometry": {"type": f["geometry"]["type"],
                         "coordinates": round_coords(f["geometry"]["coordinates"], 5)},
            "properties": {
                "geoid": p["GEOID"],
                "name": f"Block group {p['BLKGRP']}, tract {p['TRACT'][:4]}.{p['TRACT'][4:]}",
                "addresses": n,
            },
        })
    features.sort(key=lambda f: f["properties"]["geoid"])
    if not features:
        raise SystemExit("No block group contains a city address point; check inputs.")
    return {"type": "FeatureCollection", "features": features}


def main() -> int:
    with open(BOUNDARY, encoding="utf-8") as fh:
        boundary = json.load(fh)
    with open(ADDRESS_POINTS, encoding="utf-8") as fh:
        points = json.load(fh)["points"]
    tiger = fetch(bbox_of(boundary))
    fc = select_block_groups(tiger, points)
    write_geojson(OUT, fc)
    print(f"Wrote {len(fc['features'])} block groups (of {len(tiger['features'])} in bbox) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
