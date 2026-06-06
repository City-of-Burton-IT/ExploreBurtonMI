"""Pure public-safe validation gate.

Enforces the property allowlist (strips anything else), requires a name and a
valid in-bounds Point geometry, and FAILS LOUD (raises) on schema violations so a
broken record can never silently reach the public site.
"""
from __future__ import annotations

ALLOWED_PROPERTIES = {
    "name",
    "category",
    "address",
    "phone",
    "website",
    "hours",
    "description",
    "services",  # list of in-store services on a collapsed big-box record (display only)
}


class ValidationError(Exception):
    pass


def validate(features: list, bbox: list) -> list:
    """bbox = [min_lat, min_lng, max_lat, max_lng]. Returns cleaned features."""
    min_lat, min_lng, max_lat, max_lng = bbox
    cleaned = []
    errors = []

    for f in features:
        fid = f.get("id", "<no id>")
        # offMap: a hand-curated facility whose real location is outside the city
        # (e.g. a permit-issued service at an out-of-town facility). It is listed
        # and searchable but not plotted on the locked city map, so it alone is
        # exempt from the in-bounds check. Every other gate still applies.
        # The flag is honored ONLY on curated ('burton:') ids. The OSM/Overture
        # normalizers build features from explicit keys (no top-level spread), so
        # they cannot carry an offMap field; this id guard ENFORCES that - an
        # auto-sourced record can never use the flag to escape the bounds check.
        off_map = bool(f.get("offMap")) and str(f.get("id", "")).startswith("burton:")
        geom = f.get("geometry")
        if not geom or geom.get("type") != "Point":
            errors.append(f"{fid}: missing or non-Point geometry")
            continue
        coords = geom.get("coordinates") or []
        if len(coords) != 2 or not all(isinstance(c, (int, float)) for c in coords):
            errors.append(f"{fid}: invalid coordinates {coords!r}")
            continue
        lng, lat = coords[0], coords[1]
        if not off_map and not (min_lng <= lng <= max_lng and min_lat <= lat <= max_lat):
            errors.append(f"{fid}: coordinates out of bounds ({lat}, {lng})")
            continue

        props = f.get("properties") or {}
        if not props.get("name"):
            errors.append(f"{fid}: missing properties.name")
            continue

        safe_props = {k: v for k, v in props.items() if k in ALLOWED_PROPERTIES}
        feature = {
            "type": "Feature",
            "id": fid,
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": safe_props,
        }
        if off_map:
            feature["offMap"] = True
        cleaned.append(feature)

    if errors:
        raise ValidationError(
            "public-safe validation failed:\n - " + "\n - ".join(errors)
        )
    return cleaned
