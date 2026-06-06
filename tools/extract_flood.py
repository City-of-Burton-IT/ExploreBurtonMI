# Build public/flood-zones.geojson: FEMA high-risk flood zones over Burton, as a
# map overlay ("am I in a flood zone?").
#
# Source: FEMA National Flood Hazard Layer (NFHL), the official public flood-map
# data, served from FEMA's ArcGIS REST endpoint (layer 28 = Flood Hazard Zones).
# Public data, redistributable. We keep only Special Flood Hazard Areas
# (SFHA_TF='T' -- the 1%-annual-chance / high-risk zones like AE and A), which is
# what residents care about; the low-risk "X" areas (most of the map) are omitted
# to keep the overlay legible.
#
# The query envelope is derived from public/boundary.geojson so it tracks the city
# automatically. Geometry is generalized server-side and rounded to 5 decimals to
# keep the committed file small.
#
# Re-runnable:  python tools/extract_flood.py
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
OUT = os.path.join(ROOT, "public", "flood-zones.geojson")

SERVICE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
FLOOD_BLUE = "#1e6fb8"
PAGE = 1000  # FEMA maxRecordCount


def _round(coords, ndigits=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], ndigits), round(coords[1], ndigits)]
    return [_round(c, ndigits) for c in coords]


def boundary_bbox(pad: float = 0.004) -> tuple[float, float, float, float]:
    with open(BOUNDARY, "r", encoding="utf-8") as fh:
        gj = json.load(fh)
    geom = gj["geometry"] if gj.get("type") == "Feature" else (
        gj["features"][0]["geometry"] if gj.get("features") else gj
    )
    xs: list[float] = []
    ys: list[float] = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0])
            ys.append(c[1])
        else:
            for sub in c:
                walk(sub)

    walk(geom["coordinates"])
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def fetch(bbox: tuple[float, float, float, float]) -> list:
    features: list = []
    offset = 0
    while True:
        params = {
            "where": "SFHA_TF='T'",  # Special Flood Hazard Area = high risk
            "geometry": ",".join(str(round(v, 5)) for v in bbox),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FLD_ZONE",
            "maxAllowableOffset": "0.0002",  # ~20 m generalization
            "returnGeometry": "true",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE),
            "f": "geojson",
        }
        url = SERVICE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            fc = json.load(resp)
        page = fc.get("features", [])
        features.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return features


def main() -> int:
    bbox = boundary_bbox()
    raw = fetch(bbox)
    if not raw:
        raise SystemExit("No FEMA flood zones returned (check the NFHL service / bbox).")

    features = []
    zones: dict[str, int] = {}
    for f in raw:
        geom = f.get("geometry")
        if not geom:
            continue
        zone = (f.get("properties", {}) or {}).get("FLD_ZONE", "")
        zones[zone] = zones.get(zone, 0) + 1
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"FEMA Flood Zone {zone} - high risk (1% annual chance)",
                "zone": zone,
                "_color": FLOOD_BLUE,
                "_fillOpacity": 0.35,  # filled, not just outlined
                "_weight": 1,
            },
            "geometry": {"type": geom["type"], "coordinates": _round(geom["coordinates"])},
        })

    fc = {
        "type": "FeatureCollection",
        "_source": (
            "FEMA National Flood Hazard Layer (NFHL), Flood Hazard Zones. Special Flood "
            "Hazard Areas (1%-annual-chance / high-risk) only, clipped to the Burton area."
        ),
        "features": features,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  {len(features)} flood-zone polygons; zones: {zones}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
