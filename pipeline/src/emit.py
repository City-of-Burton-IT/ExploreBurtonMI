"""Write the final FeatureCollection, sorted by ID for clean, reviewable diffs."""
from __future__ import annotations

import json

# 6 decimal places ~= 0.11 m at this latitude -- far finer than any civic map needs.
# Some sources (Overture) carried 11+ digits, bloating the published file.
COORD_DP = 6


def _round_coords(feature: dict) -> dict:
    geom = feature.get("geometry")
    if geom and geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
        geom["coordinates"] = [round(c, COORD_DP) for c in geom["coordinates"]]
    return feature


def emit(features: list, path: str) -> int:
    ordered = [_round_coords(f) for f in sorted(features, key=lambda f: f["id"])]
    fc = {"type": "FeatureCollection", "features": ordered}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return len(ordered)
