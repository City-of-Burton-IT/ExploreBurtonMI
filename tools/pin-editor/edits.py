# Pin-editor edit-routing core: translate map edits into source-file changes.
#
# Pure functions only -- no file IO, no Flask. A pin's id PREFIX decides where an
# edit lands:
#   curated   (burton: / manual:)  -> facilities.geojson  (edit in place / remove / add)
#   discovered (osm: / overture:)   -> overrides.json      (coordinates / field / hidden)
#
# apply_edits() deep-copies its inputs and returns new (facilities, overrides) dicts.
from __future__ import annotations

import copy
import re

_CURATED_PREFIXES = ("burton:", "manual:")
_DEFAULT_DELETE_WHY = "Removed via pin editor."


def is_curated(feature_id: str) -> bool:
    """True for hand-curated pins (live in facilities.geojson)."""
    return str(feature_id).startswith(_CURATED_PREFIXES)


def slugify(name: str) -> str:
    """A url-safe slug: drop apostrophes, collapse other non-alnum runs to '-'."""
    s = str(name).lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "pin"


def unique_manual_id(name: str, existing_ids) -> str:
    """A `manual:<slug>` id not already in existing_ids, suffixed -2, -3, ... on collision."""
    base = f"manual:{slugify(name)}"
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


def _facility_by_id(facilities: dict, fid: str):
    for f in facilities["features"]:
        if f.get("id") == fid:
            return f
    return None


def apply_edits(facilities: dict, overrides: dict, edits: list) -> tuple[dict, dict]:
    """Apply a list of edit ops, routing each to the right source file. Pure.

    Edit op shapes:
      {"op": "add",    "name", "category", "coordinates": [lng,lat], "fields": {...}?}
      {"op": "move",   "id", "coordinates": [lng,lat]}
      {"op": "edit",   "id", "fields": {field: value, ...}}
      {"op": "delete", "id", "why"?}
    """
    facilities = copy.deepcopy(facilities)
    overrides = copy.deepcopy(overrides)
    existing_ids = {f.get("id") for f in facilities["features"]} | set(overrides.keys())

    for edit in edits:
        op = edit.get("op")

        if op == "add":
            fid = unique_manual_id(edit["name"], existing_ids)
            existing_ids.add(fid)
            props = {"name": edit["name"], "category": edit["category"]}
            for k, v in (edit.get("fields") or {}).items():
                if v not in (None, ""):
                    props[k] = v
            facilities["features"].append({
                "type": "Feature",
                "id": fid,
                "geometry": {"type": "Point", "coordinates": list(edit["coordinates"])},
                "properties": props,
            })
            continue

        fid = edit["id"]
        curated = is_curated(fid)

        if op == "move":
            coords = list(edit["coordinates"])
            if curated:
                feat = _facility_by_id(facilities, fid)
                if feat is not None:
                    feat["geometry"] = {"type": "Point", "coordinates": coords}
            else:
                overrides.setdefault(fid, {})["coordinates"] = coords

        elif op == "edit":
            fields = edit.get("fields") or {}
            if curated:
                feat = _facility_by_id(facilities, fid)
                if feat is not None:
                    for k, v in fields.items():
                        if feat["properties"].get(k) != v:   # skip no-op field writes
                            feat["properties"][k] = v
            else:
                entry = overrides.setdefault(fid, {})
                for k, v in fields.items():
                    entry[k] = v

        elif op == "delete":
            if curated:
                facilities["features"] = [
                    f for f in facilities["features"] if f.get("id") != fid
                ]
            else:
                overrides[fid] = {"hidden": True, "_why": edit.get("why") or _DEFAULT_DELETE_WHY}

    return facilities, overrides
