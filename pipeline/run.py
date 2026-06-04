"""Explore Burton data pipeline.

Merges OpenStreetMap businesses with curated city facilities, geocodes
address-only records, applies manual overrides, validates public-safe, and emits
public/data.geojson for the viewer.

Usage:
    python run.py            # use cached OSM/boundary if present
    python run.py --refresh  # re-fetch OSM + boundary from the network
"""
from __future__ import annotations

import os
import sys

from src import util
from src.fetch_boundary import fetch_boundary
from src.fetch_osm import fetch_osm
from src.normalize import normalize_all
from src.normalize_overture import normalize_overture, load_snapshot, filter_residential
from src.clip import clip_features, bounds_of
from src.geocode import geocode_features
from src.merge import merge
from src.validate import validate
from src.emit import emit


def main(refresh: bool = False) -> int:
    config = util.load_config()
    category_map = util.load_json(config["paths"]["category_map"])
    overrides = util.load_json(config["paths"]["overrides"])
    facilities = util.load_json(config["paths"]["facilities"])["features"]
    tag_keys = config["overpass"]["tag_keys"]

    print("1. boundary ...", end=" ", flush=True)
    boundary = fetch_boundary(config, force=refresh)
    # Publish the clip polygon so the viewer's city-limits outline always matches
    # the boundary features were clipped to.
    util.save_json("../public/boundary.geojson", boundary)
    print(boundary.get("type"))

    print("2. OSM fetch ...", end=" ", flush=True)
    elements = fetch_osm(config, force=refresh)
    print(f"{len(elements)} raw elements")

    print("3. normalize ...", end=" ", flush=True)
    osm_features = normalize_all(elements, category_map, tag_keys)
    print(f"{len(osm_features)} named+categorized")

    print("4. clip to boundary ...", end=" ", flush=True)
    osm_features = clip_features(osm_features, boundary)
    print(f"{len(osm_features)} inside Burton")

    print("4b. overture places ...", end=" ", flush=True)
    overture_features: list = []
    overture_path = util.path(config["paths"]["overture"])
    if os.path.exists(overture_path):
        ov_map = util.load_json(config["paths"]["overture_category_map"])
        ov_cfg = config.get("overture", {})
        snapshot = load_snapshot(overture_path)
        snapshot, dropped_resi = filter_residential(snapshot, ov_cfg.get("exclude_categories", []))
        overture_features, ov_defaulted = normalize_overture(
            snapshot, ov_map, ov_cfg.get("min_confidence", 0.0),
            tuple(ov_cfg.get("skip_burton_categories", [])),
        )
        overture_features = clip_features(overture_features, boundary)
        print(
            f"{len(overture_features)} inside Burton "
            f"({dropped_resi} home-prone dropped, {ov_defaulted} defaulted category)"
        )
    else:
        print("no snapshot (skipped) -- run tools/extract_overture.py to add")

    print("5. geocode facilities ...", end=" ", flush=True)
    facilities, misses = geocode_features(facilities, config)
    print(f"{len(facilities)} facilities, {len(misses)} geocode miss(es)")
    for fid, why in misses:
        print(f"     ! {fid}: {why} (needs a 'coordinates' override)")

    print("6. merge + overrides ...", end=" ", flush=True)
    # Overrides (which may supply coordinates) are applied inside merge, so do this
    # BEFORE dropping records that still lack geometry. OSM precedes Overture so an
    # OSM record wins over an Overture duplicate at the same site (proximity dedup
    # keeps the first occurrence); curated facilities still win over both.
    discovered = osm_features + overture_features
    merged = merge(discovered, facilities, overrides, config.get("dedupe", {}).get("threshold_m", 60.0))
    no_geom = [f["id"] for f in merged if not f.get("geometry")]
    merged = [f for f in merged if f.get("geometry")]
    print(f"{len(merged)} merged")
    for fid in no_geom:
        print(f"     ! dropped {fid}: no geometry after geocode+overrides")

    print("7. validate public-safe ...", end=" ", flush=True)
    # Validation bbox = the boundary's own extent (+ small epsilon), so anything
    # that passed the clip also passes validation.
    b = bounds_of(boundary)
    eps = 0.01
    bbox = [b[0] - eps, b[1] - eps, b[2] + eps, b[3] + eps]
    clean = validate(merged, bbox)
    print(f"{len(clean)} valid")

    print("8. emit ...", end=" ", flush=True)
    out = config["paths"]["output"]
    count = emit(clean, util.path(out))
    print(f"wrote {count} features -> {out}")

    # category breakdown
    counts: dict = {}
    for f in clean:
        c = f["properties"].get("category", "(none)")
        counts[c] = counts.get(c, 0) + 1
    print("\nCategory breakdown:")
    for cat, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {cat}")
    return 0


if __name__ == "__main__":
    sys.exit(main(refresh="--refresh" in sys.argv))
