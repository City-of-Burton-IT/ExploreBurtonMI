"""Geocode address-only records (null geometry) via the free US Census geocoder.

Results are cached by address. Records that fail to geocode are left with null
geometry and reported as misses (the validate step will then reject them, so a
miss is loud rather than silent).
"""
from __future__ import annotations

import os

from . import util


def _load_cache() -> dict:
    cache = util.path("data/cache/geocode.json")
    return util.load_json(cache) if os.path.exists(cache) else {}


def _save_cache(cache: dict) -> None:
    util.save_json("data/cache/geocode.json", cache)


def geocode_address(address: str, config: dict, cache: dict):
    if address in cache:
        return cache[address]
    cfg = config["census_geocoder"]
    data = util.http_get_json(
        cfg["endpoint"],
        {"address": address, "benchmark": cfg["benchmark"], "format": "json"},
        config["overpass"]["user_agent"],
    )
    matches = data.get("result", {}).get("addressMatches", [])
    coords = None
    if matches:
        c = matches[0]["coordinates"]
        coords = [c["x"], c["y"]]
    cache[address] = coords
    return coords


def geocode_features(features: list, config: dict):
    """Fill null geometries from addresses. Returns (features, misses)."""
    cache = _load_cache()
    misses = []
    for f in features:
        if f.get("geometry"):
            continue
        address = (f.get("properties") or {}).get("address")
        if not address:
            misses.append((f.get("id"), "no address to geocode"))
            continue
        coords = geocode_address(address, config, cache)
        if coords:
            f["geometry"] = {"type": "Point", "coordinates": coords}
        else:
            misses.append((f.get("id"), f"no geocode match for {address!r}"))
    _save_cache(cache)
    return features, misses
