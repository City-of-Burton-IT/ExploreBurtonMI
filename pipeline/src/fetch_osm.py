"""Fetch named OSM features (businesses/amenities) in the Burton bbox via Overpass.

Caches the raw element list so re-runs don't hammer the public API.
"""
from __future__ import annotations

import os

from . import util


def build_query(bbox: list, tag_keys: list) -> str:
    s, w, n, e = bbox
    box = f"({s},{w},{n},{e})"
    parts = []
    for key in tag_keys:
        parts.append(f'  node["{key}"]["name"]{box};')
        parts.append(f'  way["{key}"]["name"]{box};')
    body = "\n".join(parts)
    return f"[out:json][timeout:90];\n(\n{body}\n);\nout center tags;"


def fetch_osm(config: dict, force: bool = False) -> list:
    cache = util.path(config["paths"]["osm_cache"])
    if os.path.exists(cache) and not force:
        return util.load_json(cache).get("elements", [])

    oc = config["overpass"]
    query = build_query(oc["bbox"], oc["tag_keys"])
    data = util.http_post_json(oc["endpoint"], {"data": query}, oc["user_agent"])
    util.save_json(cache, data)
    return data.get("elements", [])
