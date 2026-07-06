# Build public/school-districts.geojson: the public school districts that serve the
# City of Burton, as a map overlay layer.
#
# Source: US Census cartographic boundary file (1:500,000), Michigan (FIPS 26),
# Unified School Districts, federal public-domain data. Downloaded, read with pyshp
# (pure-Python; no GDAL/shapely, matching the pipeline), filtered to the districts whose
# polygons cover any point inside Burton's boundary, then written as GeoJSON. The
# committed output is what the site reads.
#
# Re-runnable:
#     python tools/extract_school_districts.py [--year 2023]
#
# Which districts "serve Burton" is derived from public/boundary.geojson each run, so it
# stays correct if the boundary changes, not hard-coded.
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile

from lib.geo import round_coords
from lib.httpio import get_bytes
from lib.iox import write_geojson
from lib.paths import public_path

STATE_FIPS = "26"  # Michigan
CB_URL = "https://www2.census.gov/geo/tiger/GENZ{year}/shp/cb_{year}_{state}_unsd_500k.zip"
BOUNDARY = public_path("boundary.geojson")
OUT = public_path("school-districts.geojson")


def _rings(geom: dict) -> list:
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def _pip(x: float, y: float, ring: list) -> bool:
    """Ray-casting point-in-ring."""
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


def _shape_contains(geo: dict, x: float, y: float) -> bool:
    """Even-odd test across all rings of a (Multi)Polygon geo-interface dict."""
    inside = False
    for poly in _rings(geo):
        for ring in poly:
            if _pip(x, y, ring):
                inside = not inside
    return inside


def _round_geo(geo: dict, ndigits: int = 5) -> dict:
    """Round coordinates (~1 m at this latitude) to shrink the output file."""
    return {"type": geo["type"], "coordinates": round_coords(geo["coordinates"], ndigits)}


def burton_interior_points(n: int = 60) -> list[tuple[float, float]]:
    boundary = json.load(open(BOUNDARY, encoding="utf-8"))
    rings = _rings(boundary)
    xs = [p[0] for poly in rings for ring in poly for p in ring]
    ys = [p[1] for poly in rings for ring in poly for p in ring]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    pts = []
    for i in range(n):
        for k in range(n):
            x = minx + (maxx - minx) * i / (n - 1)
            y = miny + (maxy - miny) * k / (n - 1)
            if any(_pip(x, y, poly[0]) for poly in rings):
                pts.append((x, y))
    if not pts:
        raise SystemExit("No interior points found, check public/boundary.geojson")
    return pts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Burton school-district overlay.")
    parser.add_argument("--year", default="2023", help="Cartographic boundary vintage (default 2023)")
    parser.add_argument("--shp", help="Path to an already-extracted cb_*_unsd_500k shapefile (skips download)")
    args = parser.parse_args()

    try:
        import shapefile  # pyshp
    except ImportError:
        raise SystemExit("pyshp is required: pip install pyshp (see tools/requirements.txt)")

    if args.shp:
        reader = shapefile.Reader(args.shp)
    else:
        url = CB_URL.format(year=args.year, state=STATE_FIPS)
        print(f"Downloading {url} ...")
        zf = zipfile.ZipFile(io.BytesIO(get_bytes(url)))
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        reader = shapefile.Reader(
            shp=io.BytesIO(zf.read(base + ".shp")),
            dbf=io.BytesIO(zf.read(base + ".dbf")),
            shx=io.BytesIO(zf.read(base + ".shx")),
        )

    fields = [f[0] for f in reader.fields[1:]]
    gi, ni = fields.index("GEOID"), fields.index("NAME")
    pts = burton_interior_points()

    features = []
    for rec, shp in zip(reader.records(), reader.shapes()):
        bx = shp.bbox  # [minx, miny, maxx, maxy]
        if bx[2] < min(p[0] for p in pts) or bx[0] > max(p[0] for p in pts):
            continue
        if bx[3] < min(p[1] for p in pts) or bx[1] > max(p[1] for p in pts):
            continue
        geo = shp.__geo_interface__
        if any(_shape_contains(geo, x, y) for x, y in pts):
            features.append({
                "type": "Feature",
                "properties": {"name": rec[ni], "geoid": rec[gi]},
                "geometry": _round_geo(geo),
            })

    features.sort(key=lambda f: f["properties"]["name"])
    fc = {
        "type": "FeatureCollection",
        "_source": (
            f"U.S. Census Bureau cartographic boundary file cb_{args.year}_{STATE_FIPS}_unsd_500k "
            "(Unified School Districts, 1:500,000). Public domain. Filtered to districts serving "
            "the City of Burton."
        ),
        "features": features,
    }
    write_geojson(OUT, fc)
    print(f"Wrote {OUT}")
    print(f"  {len(features)} districts serving Burton:")
    for f in features:
        print(f"    {f['properties']['geoid']}  {f['properties']['name']}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
