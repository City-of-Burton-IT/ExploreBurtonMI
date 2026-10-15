"""Derive parcel centroids and outlines from the City's parcel shapefile
(\\\\burtonmi1a\\Pictometry\\City of Burton_Parcels<year>.shp, Michigan State Plane
South, NAD83 HARN, international feet).

The shapefile's attribute table carries owner names, mailing addresses and
assessed values, so the shapefile itself is NEVER committed: drop it under
pipeline/data/parcels/ (gitignored). This tool reads only the parcel number and
the geometry and writes two gitignored derived files:

    pipeline/data/parcel-centroids.csv   parcel, lat, lng      (one row per parcel)
    pipeline/data/parcel-polygons.json   {parcel: [[lng, lat], ...]} outer ring, ~1 m

Consumers: build_business_sites.py (centroids for vacant lots with no street
number, outlines for the vacant-sites overlay), build_sales_tiles.py and
build_new_homes.py (centroids by parcel number before the address geocoder).

Projection is inverted by hand (Lambert Conformal Conic, two standard parallels,
GRS80) because the pipeline venv deliberately has no pyproj; the result is
checked against a known geocoded address in main().

    pipeline/.venv/Scripts/python tools/extract_parcel_centroids.py [--shp path]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

import shapefile  # pyshp

from lib.iox import write_json
from lib.paths import pipeline_data_path

DEFAULT_SHP = pipeline_data_path("parcels", "parcels.shp")
OUT_CENTROIDS = pipeline_data_path("parcel-centroids.csv")
OUT_POLYGONS = pipeline_data_path("parcel-polygons.json")
PARCEL_FIELDS = ("pnum", "ParIDShort")

# NAD_1983_HARN_StatePlane_Michigan_South_FIPS_2113_Feet_Intl (from the .prj)
FT = 0.3048
FALSE_E = 13123359.58005249 * FT
FALSE_N = 0.0
LON0 = math.radians(-84.36666666666666)
LAT1 = math.radians(42.1)
LAT2 = math.radians(43.66666666666666)
LAT0 = math.radians(41.5)
A = 6378137.0
F = 1 / 298.257222101
E = math.sqrt(2 * F - F * F)


def _m(phi: float) -> float:
    return math.cos(phi) / math.sqrt(1 - (E * math.sin(phi)) ** 2)


def _t(phi: float) -> float:
    return math.tan(math.pi / 4 - phi / 2) / ((1 - E * math.sin(phi)) / (1 + E * math.sin(phi))) ** (E / 2)


_N = (math.log(_m(LAT1)) - math.log(_m(LAT2))) / (math.log(_t(LAT1)) - math.log(_t(LAT2)))
_FF = _m(LAT1) / (_N * _t(LAT1) ** _N)
_RHO0 = A * _FF * _t(LAT0) ** _N


def to_lonlat(x_ft: float, y_ft: float) -> tuple[float, float]:
    """State Plane feet -> (lng, lat) degrees, LCC 2SP inverse (Snyder 15-9..15-11)."""
    x = x_ft * FT - FALSE_E
    y = y_ft * FT - FALSE_N
    rho = math.copysign(math.hypot(x, _RHO0 - y), _N)
    theta = math.atan2(x, _RHO0 - y) if _N > 0 else math.atan2(-x, y - _RHO0)
    t = (rho / (A * _FF)) ** (1 / _N)
    phi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(8):
        es = E * math.sin(phi)
        phi = math.pi / 2 - 2 * math.atan(t * ((1 - es) / (1 + es)) ** (E / 2))
    return math.degrees(LON0 + theta / _N), math.degrees(phi)


def ring_centroid(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """Area-weighted centroid of a closed ring (shoelace); falls back to the mean
    for degenerate rings."""
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-9:
        return sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def outer_ring(shape) -> list[tuple[float, float]]:
    """The largest ring of a (multi)polygon shape, in source units."""
    parts = list(shape.parts) + [len(shape.points)]
    rings = [shape.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
    return max(rings, key=lambda r: abs(sum(
        r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))))


def extract(shp_path: str) -> tuple[dict[str, tuple[float, float]], dict[str, list]]:
    reader = shapefile.Reader(shp_path)
    names = [f[0] for f in reader.fields[1:]]
    field = next((f for f in PARCEL_FIELDS if f in names), None)
    if field is None:
        raise SystemExit(f"parcel shapefile has no parcel-number field among {PARCEL_FIELDS}: {names}")
    idx = names.index(field)
    centroids: dict[str, tuple[float, float]] = {}
    polygons: dict[str, list] = {}
    skipped = 0
    for rec, shape in zip(reader.iterRecords(fields=[field]), reader.iterShapes()):
        pnum = str(rec[0] if len(rec) == 1 else rec[idx]).strip()
        if not pnum or not shape.points:
            skipped += 1
            continue
        ring = outer_ring(shape)
        cx, cy = ring_centroid(ring)
        lng, lat = to_lonlat(cx, cy)
        centroids[pnum] = (round(lat, 6), round(lng, 6))
        polygons[pnum] = [[round(v, 5) for v in to_lonlat(x, y)] for x, y in ring]
    if skipped:
        print(f"  skipped {skipped} records without a parcel number or geometry")
    if len(centroids) < 10_000:
        raise SystemExit(f"Only {len(centroids)} parcels extracted; expected ~13,000. Wrong file?")
    return centroids, polygons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", default=DEFAULT_SHP)
    args = ap.parse_args()
    if not os.path.exists(args.shp):
        raise SystemExit(f"Shapefile not found: {args.shp}\nCopy the .shp/.shx/.dbf/.prj set from "
                         "\\\\burtonmi1a\\Pictometry to pipeline/data/parcels/parcels.* (gitignored).")
    centroids, polygons = extract(args.shp)
    with open(OUT_CENTROIDS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parcel", "lat", "lng"])
        for pnum in sorted(centroids):
            w.writerow([pnum, *centroids[pnum]])
    write_json(OUT_POLYGONS, polygons)
    # Sanity check against a geocoded City address if the cache has one.
    cache = pipeline_data_path("cache", "address_geocode.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            c = json.load(fh)
        ref = c.get("4303 S CENTER RD, BURTON, MI, 48519") or c.get("4303 S CENTER RD, Burton, MI, ")
        hall = centroids.get("59-23-200-013")  # City Hall parcel, if that is its number
        if ref and hall:
            d = math.hypot((hall[1] - ref[1]) * 111320 * math.cos(math.radians(ref[0])), (hall[0] - ref[0]) * 110540)
            print(f"  City Hall check: centroid is {d:.0f} m from the geocoded address")
    print(f"Wrote {len(centroids)} centroids -> {OUT_CENTROIDS} and outlines -> {OUT_POLYGONS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
