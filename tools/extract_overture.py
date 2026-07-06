#!/usr/bin/env python3
# Out-of-band Overture Maps Places extractor for Explore Burton.
#
# This tool carries the heavy binary readers (the overturemaps CLI / DuckDB /
# pyarrow) so the pipeline does NOT have to. It pulls the Burton-bbox 'place'
# features from the latest Overture release, trims them to a public-safe slim
# schema, filters by confidence, and writes a committed snapshot that the pure-
# Python pipeline reads like a curated input.
#
# Overture Places is licensed CDLA-Permissive 2.0, redistributable with
# attribution (add "(c) Overture Maps Foundation" to the viewer attribution when
# the snapshot first ships).
#
# Usage (from repo root, in a venv with tools/requirements.txt installed):
#     python tools/extract_overture.py
#     python tools/extract_overture.py --raw downloaded.geojson   # skip the CLI
#     python tools/extract_overture.py --min-confidence 0.6
#
# Review the diff on pipeline/data/overture_places.geojson before running the
# pipeline + shipping.
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from lib.iox import write_json
from lib.paths import REPO_ROOT, pipeline_data_path

CONFIG = Path(REPO_ROOT) / "pipeline" / "config.json"
DEFAULT_OUT = Path(pipeline_data_path("overture_places.geojson"))


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        return json.load(fh)


def bbox_to_wsen(bbox: list) -> str:
    """config bbox is [min_lat, min_lng, max_lat, max_lng]; overturemaps wants
    west,south,east,north = min_lng,min_lat,max_lng,max_lat."""
    min_lat, min_lng, max_lat, max_lng = bbox
    return f"{min_lng},{min_lat},{max_lng},{max_lat}"


def download_places(bbox_wsen: str, dest: Path) -> None:
    """Download Overture 'place' features for the bbox via the overturemaps CLI."""
    exe = shutil.which("overturemaps")
    cmd = (
        [exe] if exe else [sys.executable, "-m", "overturemaps"]
    ) + ["download", f"--bbox={bbox_wsen}", "-f", "geojson", "--type=place", "-o", str(dest)]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise SystemExit(
            "overturemaps not found. Install it first:\n"
            "  pip install -r tools/requirements.txt"
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"overturemaps download failed (exit {e.returncode}).")


def _as_obj(value: Any) -> Any:
    """Return value as a Python object, decoding a JSON-encoded string if needed.
    The overturemaps CLI's GeoJSON writer may emit Overture struct/list fields as
    nested objects OR as JSON-encoded strings depending on version, handle both."""
    if isinstance(value, str) and value.strip()[:1] in "{[":
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _primary(props: dict, field: str) -> str:
    """Extract <field>.primary whether the CLI emits the struct as a nested dict, a
    JSON-encoded string, a flattened '<field>.primary' key, or a bare string."""
    val = _as_obj(props.get(field))
    if isinstance(val, dict):
        return str(val.get("primary") or "").strip()
    if isinstance(val, str) and val.strip():
        return val.strip()  # bare string: the name itself / the category code
    flat = props.get(f"{field}.primary") or props.get(f"{field}_primary")
    return str(flat).strip() if flat else ""


def _first(value: Any) -> str:
    value = _as_obj(value)
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value).strip() if value else ""


def _build_address(addresses: Any) -> str:
    addresses = _as_obj(addresses)
    if not isinstance(addresses, list) or not addresses:
        return ""
    a = addresses[0] or {}
    if isinstance(a, str):
        a = _as_obj(a)
        if not isinstance(a, dict):
            return str(a).strip()
    freeform = str(a.get("freeform") or "").strip()
    locality = str(a.get("locality") or "").strip()
    region = str(a.get("region") or "").strip()
    postcode = str(a.get("postcode") or "").strip()
    tail = ", ".join(p for p in [locality, f"{region} {postcode}".strip()] if p)
    if freeform and tail:
        return f"{freeform}, {tail}"
    return freeform or tail


def slim_feature(feature: dict, min_confidence: float) -> dict | None:
    """Full Overture place feature -> slim snapshot feature, or None to drop."""
    props = feature.get("properties") or {}

    name = _primary(props, "names")
    if not name:
        return None

    confidence = props.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < min_confidence:
        return None

    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") != "Point" or len(coords) != 2:
        return None

    overture_category = _primary(props, "categories")

    out_props = {
        "name": name,
        "overture_category": overture_category,
        "confidence": confidence,
        "address": _build_address(props.get("addresses")),
        "phone": _first(props.get("phones")),
        "website": _first(props.get("websites")),
    }
    out_props = {k: v for k, v in out_props.items() if v not in ("", None)}

    fid = feature.get("id") or props.get("id") or ""
    return {
        "type": "Feature",
        "id": str(fid),
        "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
        "properties": out_props,
    }


def slim_collection(raw: dict, min_confidence: float) -> list:
    features = raw.get("features")
    if raw.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise SystemExit("downloaded file is not a GeoJSON FeatureCollection")
    out = []
    for f in features:
        slim = slim_feature(f, min_confidence)
        if slim:
            out.append(slim)
    return out


def parse_args() -> argparse.Namespace:
    config = load_config()
    p = argparse.ArgumentParser(description="Extract a Burton Overture Places snapshot.")
    p.add_argument("--raw", type=Path, default=None,
                   help="Use an already-downloaded Overture GeoJSON instead of calling the CLI.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Snapshot output path.")
    p.add_argument("--min-confidence", type=float,
                   default=config.get("overture", {}).get("min_confidence", 0.0),
                   help="Drop places below this Overture confidence score.")
    p.set_defaults(_config=config)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = args._config

    if args.raw:
        raw_path = args.raw
    else:
        bbox = bbox_to_wsen(config["overture"]["bbox"])
        tmp = Path(tempfile.gettempdir()) / "overture_burton_raw.geojson"
        print(f"Downloading Overture places for bbox {bbox} ...")
        download_places(bbox, tmp)
        raw_path = tmp

    with raw_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    features = slim_collection(raw, args.min_confidence)
    features.sort(key=lambda f: f["id"])
    collection = {"type": "FeatureCollection", "features": features}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(str(args.out), collection)
    print(f"Wrote {len(features):,} slim places -> {args.out}")
    print("Review the diff, then run: cd pipeline; .venv\\Scripts\\python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
