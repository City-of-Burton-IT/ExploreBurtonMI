"""Write the final FeatureCollection, sorted by ID for clean, reviewable diffs."""
from __future__ import annotations

import json


def emit(features: list, path: str) -> int:
    ordered = sorted(features, key=lambda f: f["id"])
    fc = {"type": "FeatureCollection", "features": ordered}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return len(ordered)
