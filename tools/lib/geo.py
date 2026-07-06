# GeoJSON coordinate helpers.
from __future__ import annotations


def round_coords(coords, ndigits: int = 5):
    """Round a (nested) GeoJSON coordinate array to ndigits (~1 m at 5).

    Keeps committed overlay files small; works on any geometry's coordinates
    (Point pairs through MultiPolygon nesting).
    """
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], ndigits), round(coords[1], ndigits)]
    return [round_coords(c, ndigits) for c in coords]
