"""Pure transform: an Overpass OSM element -> our GeoJSON feature, or None.

Returns None when the element has no name or maps to no category (so noise like
benches, parking, and ATMs is dropped). No network, no external deps.
"""
from __future__ import annotations


def category_for(tags: dict, category_map: dict, tag_keys: list) -> str | None:
    """First category produced by the tags, in tag_keys precedence order.

    For each key, an exact value mapping wins; otherwise the '*' default for that
    key (if any) applies.
    """
    for key in tag_keys:
        if key not in tags:
            continue
        mapping = category_map.get(key, {})
        value = tags[key]
        cat = mapping.get(value) or mapping.get("*")
        if cat:
            return cat
    return None


def _coords(element: dict):
    """Return [lng, lat] for a node, or a way's center; None if unavailable."""
    if "lat" in element and "lon" in element:
        return [element["lon"], element["lat"]]
    center = element.get("center")
    if center:
        return [center["lon"], center["lat"]]
    return None


def _address(tags: dict) -> str | None:
    street = tags.get("addr:street")
    if not street:
        return None
    num = tags.get("addr:housenumber", "").strip()
    line1 = f"{num} {street}".strip()
    city = tags.get("addr:city", "Burton")
    state = tags.get("addr:state", "MI")
    postcode = tags.get("addr:postcode", "")
    tail = ", ".join(p for p in [city, f"{state} {postcode}".strip()] if p)
    return f"{line1}, {tail}" if tail else line1


def normalize_element(element: dict, category_map: dict, tag_keys: list) -> dict | None:
    tags = element.get("tags") or {}
    name = tags.get("name")
    if not name:
        return None
    category = category_for(tags, category_map, tag_keys)
    if not category:
        return None
    coords = _coords(element)
    if not coords:
        return None

    props = {"name": name, "category": category}
    address = _address(tags)
    if address:
        props["address"] = address
    phone = tags.get("phone") or tags.get("contact:phone")
    if phone:
        props["phone"] = phone
    website = tags.get("website") or tags.get("contact:website")
    if website:
        props["website"] = website
    hours = tags.get("opening_hours")
    if hours:
        props["hours"] = hours

    return {
        "type": "Feature",
        "id": f"osm:{element['type']}/{element['id']}",
        "geometry": {"type": "Point", "coordinates": coords},
        "properties": props,
    }


def normalize_all(elements: list, category_map: dict, tag_keys: list) -> list:
    out = []
    for el in elements:
        feat = normalize_element(el, category_map, tag_keys)
        if feat:
            out.append(feat)
    return out
