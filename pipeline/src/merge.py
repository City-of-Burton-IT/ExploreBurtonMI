"""Pure merge of the data layers + per-ID override application.

Order: curated facilities first, then OSM features (OSM dropped when its name
duplicates a curated facility - the curated record wins). Overrides are applied
last, keyed by feature ID, so re-fetching OSM never clobbers manual corrections.
"""
from __future__ import annotations

import math
import re

# Generic words that one source appends to a business name and another omits
# ("Marathon" vs "Marathon Gas", "Admiral" vs "Admiral Petroleum Co"). They are
# stripped before comparing names, so two records at one site whose names differ
# only by these words collapse into one pin. Substantive words ("School",
# "Church", "Pharmacy") are deliberately NOT here: "Blessed Sacrament" and
# "Blessed Sacrament School" are different places that happen to share a site.
_GENERIC_NAME_WORDS = frozenset(
    {
        "the", "a", "an", "and", "of",
        "gas", "station", "fuel", "petroleum", "oil",
        "co", "company", "corp", "corporation", "inc", "incorporated",
        "llc", "llp", "ltd", "pc", "pllc", "plc",
        "store", "shop",
    }
)

_PUNCT_RE = re.compile(r"[^a-z0-9]+")


def _norm_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _core_name(name: str) -> str:
    """Lower-cased name with punctuation and generic business words removed.

    'Sunoco Gas Station' -> 'sunoco'; 'Parkside Dental Associates P.C.' ->
    'parkside dental associates'; 'The Red Baron' -> 'red baron'. Returns ''
    when nothing substantive is left, and an empty core never matches anything.
    """
    # Drop periods first so dotted abbreviations ("P.C.", "Inc.") stay one token.
    tokens = _PUNCT_RE.sub(" ", name.lower().replace(".", "")).split()
    return " ".join(t for t in tokens if t not in _GENERIC_NAME_WORDS)


def _same_place_name(a: str, b: str) -> bool:
    """True when two names identify the same business for dedupe purposes."""
    na, nb = _norm_name(a), _norm_name(b)
    if na and na == nb:
        return True
    ca, cb = _core_name(a), _core_name(b)
    return bool(ca) and ca == cb


def _haversine_m(a: list, b: list) -> float:
    """Distance in metres between two [lon, lat] points."""
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000 * math.asin(math.sqrt(h))


# Site-bound facts safe to copy between twins. Websites and descriptions are
# identity-bound and stay put: two different shops both listed under a plaza's
# name must not inherit each other's links.
_BACKFILL_KEYS = ("address", "phone")


def _fill_missing(kept: dict, dup: dict) -> None:
    """Copy the address and phone the kept record lacks from the duplicate being
    dropped, so collapsing an OSM/Overture pair never loses a contact fact that
    only one source carried. Only twins in the same category exchange values,
    and existing values on the kept record always win."""
    kp, dp = kept["properties"], dup.get("properties", {})
    if kp.get("category") != dp.get("category"):
        return
    for key in _BACKFILL_KEYS:
        value = dp.get(key)
        if value in (None, "", [], {}):
            continue
        if kp.get(key) in (None, "", [], {}):
            kp[key] = value


def dedupe_proximity(features: list, threshold_m: float = 60.0) -> list:
    """Collapse same-site duplicates: features whose names identify the same
    business (identical after normalisation, or identical once generic words
    such as 'Gas', 'Station', 'Co', 'The' are stripped) within threshold_m
    metres become one, keeping the first occurrence and back-filling any
    property it lacks from the dropped twin.

    Conservative by design - substantive words still separate places, so a
    co-located church and school ('Blessed Sacrament' vs 'Blessed Sacrament
    School') are not merged, while 'Sunoco' + 'Sunoco Gas Station' at one site
    (an OSM record and an Overture record of the same pump) are.
    """
    kept: list = []
    for f in features:
        name = f["properties"].get("name", "")
        coord = (f.get("geometry") or {}).get("coordinates")
        twin = None
        if _norm_name(name) and coord:
            for k in kept:
                if not _same_place_name(name, k["properties"].get("name", "")):
                    continue
                kc = (k.get("geometry") or {}).get("coordinates")
                if kc and _haversine_m(coord, kc) <= threshold_m:
                    twin = k
                    break
        if twin is None:
            kept.append({**f, "properties": dict(f["properties"])})
        else:
            _fill_missing(twin, f)
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
