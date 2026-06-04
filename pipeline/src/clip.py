"""Pure point-in-polygon clipping (ray casting). No external dependencies.

Works on GeoJSON Polygon and MultiPolygon geometries. A point is inside if it
falls within an exterior ring and not within any hole ring of that polygon.
"""
from __future__ import annotations


def _point_in_ring(lng: float, lat: float, ring: list) -> bool:
    """Ray-casting test for a point against a single linear ring [[lng,lat],...]."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (
            (yj - yi) or 1e-15
        ) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lng: float, lat: float, polygon: list) -> bool:
    """polygon = [exterior_ring, hole_ring, ...]."""
    if not polygon:
        return False
    if not _point_in_ring(lng, lat, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(lng, lat, hole):
            return False
    return True


def point_in_geometry(lng: float, lat: float, geometry: dict) -> bool:
    """True if (lng, lat) is inside a GeoJSON Polygon or MultiPolygon."""
    if not geometry:
        return False
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return False
    if gtype == "Polygon":
        return _point_in_polygon(lng, lat, coords)
    if gtype == "MultiPolygon":
        return any(_point_in_polygon(lng, lat, poly) for poly in coords)
    return False


def bounds_of(geometry: dict) -> list:
    """Bounding box of a Polygon/MultiPolygon as [min_lat, min_lng, max_lat, max_lng]."""
    pts: list = []

    def walk(coords):
        if coords and isinstance(coords[0], (int, float)):
            pts.append(coords)
        else:
            for c in coords:
                walk(c)

    walk(geometry.get("coordinates", []))
    lngs = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return [min(lats), min(lngs), max(lats), max(lngs)]


def clip_features(features: list, boundary_geometry: dict) -> list:
    """Keep only features whose Point geometry lies within the boundary."""
    kept = []
    for f in features:
        geom = f.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        lng, lat = geom["coordinates"][0], geom["coordinates"][1]
        if point_in_geometry(lng, lat, boundary_geometry):
            kept.append(f)
    return kept
