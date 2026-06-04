# Pure transform: a slim Overture Places snapshot feature -> our GeoJSON feature.
#
# The snapshot is produced out-of-band by tools/extract_overture.py (which carries
# the binary Overture readers); this module is pure-Python and runs in the
# pipeline. It maps Overture's raw category to a Burton category, shapes properties
# to the public-safe allowlist (so validate.py is unchanged), and prefixes ids
# 'overture:'. No network, no external deps.
from __future__ import annotations

import json
import re

# Output is restricted to these keys so the existing validate.py allowlist passes
# them through unchanged. Nothing else from the snapshot reaches the public site.
ALLOWED_OPTIONAL = ("address", "phone", "website")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def match_rule_category(raw_category: str, category_map: dict) -> str | None:
    """Map an Overture category code to a Burton category. Two passes so short,
    ambiguous codes resolve correctly: (1) an EXACT code match wins (e.g. 'bar' ->
    Dining without 'barber' colliding; 'park' -> Parks without 'parking'); (2) a
    substring keyword match, in rule order, for the consistent Overture suffixes
    (e.g. '*_restaurant', '*_church'). Returns None when nothing matches."""
    norm = _norm(raw_category)
    if not norm:
        return None
    rules = category_map.get("rules", [])
    for rule in rules:
        if norm in rule.get("exact", []):
            return rule["category"]
    for rule in rules:
        if any(kw in norm for kw in rule.get("keywords", [])):
            return rule["category"]
    return None


def match_name_hint(name: str, category_map: dict) -> str | None:
    """Category inferred from the business NAME, overriding the Overture category
    code. Needed where Overture mis-files a recognizable business type under a
    generic code (e.g. day-care centers tagged 'home_service' -> Education by name).
    Returns None when no hint matches."""
    norm = _norm(name)
    for rule in category_map.get("name_hints", []):
        if any(kw in norm for kw in rule.get("keywords", [])):
            return rule["category"]
    return None


def resolve_category(name: str, raw_category: str, category_map: dict) -> tuple[str | None, bool]:
    """Resolve a Burton category: a NAME hint wins, else the Overture category code,
    else the '_default'. Returns (category, is_default); category is None only when
    nothing matched and '_default' is null."""
    cat = match_name_hint(name, category_map) or match_rule_category(raw_category, category_map)
    if cat is not None:
        return cat, False
    return category_map.get("_default"), True


def _clean(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def normalize_feature(feature: dict, category_map: dict, min_confidence: float = 0.0,
                      skip_categories: tuple = ()) -> dict | None:
    """Slim Overture feature -> Burton feature, or None if it should be dropped."""
    props = feature.get("properties") or {}
    name = _clean(props.get("name"))
    if not name:
        return None

    confidence = props.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < min_confidence:
        return None

    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") != "Point" or len(coords) != 2:
        return None
    if not all(isinstance(c, (int, float)) for c in coords):
        return None

    category, _ = resolve_category(name, props.get("overture_category", ""), category_map)
    if category is None:
        return None  # unmapped and default disabled -> drop
    if category in skip_categories:
        return None  # civic facilities are owned by the curated layer, not Overture

    out_props = {"name": name, "category": category}
    for key in ALLOWED_OPTIONAL:
        value = _clean(props.get(key))
        if value:
            out_props[key] = value

    fid = _clean(feature.get("id")) or _norm(name)
    return {
        "type": "Feature",
        "id": f"overture:{fid}",
        "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
        "properties": out_props,
    }


def normalize_overture(features: list, category_map: dict, min_confidence: float = 0.0,
                       skip_categories: tuple = ()) -> tuple[list, int]:
    """Normalize a batch. Returns (features, defaulted_count) where defaulted_count
    is how many kept records fell through to the '_default' category (for visibility,
    so a silent catch-all bucket is never hidden). skip_categories drops records that
    map to a Burton category owned by the curated layer (civic facilities)."""
    out: list = []
    defaulted = 0
    for f in features:
        feat = normalize_feature(f, category_map, min_confidence, skip_categories)
        if feat is None:
            continue
        props = f.get("properties") or {}
        _, is_default = resolve_category(_clean(props.get("name")), props.get("overture_category", ""), category_map)
        if is_default:
            defaulted += 1
        out.append(feat)
    return out, defaulted


def is_residential(feature: dict, exclude_categories: list) -> bool:
    """True if the feature's Overture category matches a home-prone exclusion code.
    Overture has no home-based flag, so this is a blunt category-based proxy:
    trades/services typically run from a residence (handyman, lawn care, etc.). It
    will also drop a few legitimate storefront businesses in those categories --
    tune `overture.exclude_categories` in config.json to taste."""
    if not exclude_categories:
        return False
    norm = _norm((feature.get("properties") or {}).get("overture_category", ""))
    return any(kw in norm for kw in exclude_categories)


def filter_residential(features: list, exclude_categories: list) -> tuple[list, int]:
    """Drop home-prone records. Returns (kept, removed_count)."""
    kept = [f for f in features if not is_residential(f, exclude_categories)]
    return kept, len(features) - len(kept)


def load_snapshot(path: str) -> list:
    """Read an Overture snapshot FeatureCollection and return its features.
    Raises ValueError on a malformed file (fail loud)."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if raw.get("type") != "FeatureCollection" or not isinstance(raw.get("features"), list):
        raise ValueError(f"{path} is not a GeoJSON FeatureCollection")
    return raw["features"]
