"""Pure merge of the data layers + per-ID override application.

Order: curated facilities first, then OSM features (OSM dropped when its name
duplicates a curated facility - the curated record wins). Overrides are applied
last, keyed by feature ID, so re-fetching OSM never clobbers manual corrections.
"""
from __future__ import annotations

import math


def _norm_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _haversine_m(a: list, b: list) -> float:
    """Distance in metres between two [lon, lat] points."""
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000 * math.asin(math.sqrt(h))


def dedupe_proximity(features: list, threshold_m: float = 60.0) -> list:
    """Collapse same-site duplicates: features sharing an identical normalized
    name within threshold_m metres become one, keeping the first occurrence.

    Conservative by design - it matches the FULL name, so a co-located church and
    school ('Blessed Sacrament' vs 'Blessed Sacrament School') are not merged,
    while a gas station double-tagged as fuel + convenience ('Speedway' twice at
    one site) is.
    """
    kept: list = []
    for f in features:
        name = _norm_name(f["properties"].get("name", ""))
        coord = (f.get("geometry") or {}).get("coordinates")
        is_dup = False
        if name and coord:
            for k in kept:
                if _norm_name(k["properties"].get("name", "")) != name:
                    continue
                kc = (k.get("geometry") or {}).get("coordinates")
                if kc and _haversine_m(coord, kc) <= threshold_m:
                    is_dup = True
                    break
        if not is_dup:
            kept.append(f)
    return kept


def apply_override(feature: dict, override: dict) -> dict | None:
    """Return the corrected feature, or None if the override hides it."""
    if override.get("hidden"):
        return None
    props = dict(feature["properties"])
    geometry = feature.get("geometry")
    for key, value in override.items():
        if key.startswith("_") or key == "hidden":
            continue
        if key == "coordinates":
            geometry = {"type": "Point", "coordinates": value}
        else:
            props[key] = value
    return {**feature, "properties": props, "geometry": geometry}


def merge(osm_features: list, facility_features: list, overrides: dict, threshold_m: float = 60.0) -> list:
    facility_names = {
        f["properties"]["name"].strip().lower() for f in facility_features
    }

    combined = list(facility_features)
    for f in osm_features:
        if f["properties"]["name"].strip().lower() in facility_names:
            continue  # curated facility wins over an OSM duplicate
        combined.append(f)

    out = []
    for feature in combined:
        override = overrides.get(feature["id"])
        if override is not None:
            feature = apply_override(feature, override)
            if feature is None:
                continue
        out.append(feature)
    return dedupe_proximity(out, threshold_m)
