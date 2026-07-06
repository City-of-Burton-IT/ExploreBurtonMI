# Atomic JSON writes in the repo's two canonical styles: compact for committed
# GeoJSON overlays, indent=2 for panel/info JSON. Writing to a .tmp then
# os.replace()-ing means a crash mid-write can never truncate a known-good
# committed file.
from __future__ import annotations

import json
import os


def _atomic_write_text(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def write_geojson(path: str, obj: dict, ensure_ascii: bool = False) -> None:
    """Compact single-line JSON (the committed-overlay style) + trailing newline."""
    _atomic_write_text(
        path, json.dumps(obj, ensure_ascii=ensure_ascii, separators=(",", ":")) + "\n"
    )


def write_json(path: str, obj: dict, ensure_ascii: bool = False) -> None:
    """Readable indent=2 JSON (the panel/info style) + trailing newline."""
    _atomic_write_text(path, json.dumps(obj, ensure_ascii=ensure_ascii, indent=2) + "\n")
