"""Fetch the City of Burton boundary polygon.

Uses OSM/Nominatim's ready `polygon_geojson` (one cached request) as a pragmatic,
sufficient source for point-in-polygon clipping. Swappable later to the Genesee
County GIS ArcGIS layer via config (boundary.arcgis_url) if an authoritative
municipal boundary is required.
"""
from __future__ import annotations

import os

from . import util

NOMINATIM = "https://nominatim.openstreetmap.org/search"


def fetch_boundary(config: dict, force: bool = False) -> dict:
    cache = util.path(config["boundary"]["cache"])
    if os.path.exists(cache) and not force:
        return util.load_json(cache)["geometry"]

    ua = config["overpass"]["user_agent"]
    results = util.http_get_json(
        NOMINATIM,
        {
            "city": config["city_name"],
            "state": "Michigan",
            "country": "USA",
            "format": "jsonv2",
            "polygon_geojson": 1,
            "limit": 1,
        },
        ua,
    )
    if not results:
        raise RuntimeError("Nominatim returned no boundary for Burton, Michigan")
    geometry = results[0]["geojson"]
    util.save_json(cache, {"type": "Feature", "geometry": geometry, "properties": {}})
    return geometry
