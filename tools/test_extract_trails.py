# Unit tests for extract_trails pure functions (clipping, length, touch test).
# No network. Run: python -m pytest tools/test_extract_trails.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_trails as et  # noqa: E402

# A ~unit-degree square around (0,0): lon/lat in [0,1].
SQUARE = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]


def test_haversine_known_distance():
    # 1 degree of latitude is ~69 miles.
    d = et._haversine_mi([0.0, 0.0], [0.0, 1.0])
    assert 68 < d < 70, d


def test_inside_and_touches():
    assert et._inside(0.5, 0.5, SQUARE) is True
    assert et._inside(5.0, 5.0, SQUARE) is False
    bbox = et._bbox(SQUARE)
    inside_line = {"type": "LineString", "coordinates": [[0.2, 0.2], [0.8, 0.8]]}
    outside_line = {"type": "LineString", "coordinates": [[5.0, 5.0], [6.0, 6.0]]}
    assert et._touches(inside_line, SQUARE, bbox) is True
    assert et._touches(outside_line, SQUARE, bbox) is False


def test_clipped_miles_only_counts_inside_portion():
    # A line from inside the square (0.5 lat) out to 3.5 lat. Only ~0.5 deg is
    # inside (0.5 -> 1.0), so clipped length should be ~0.5 deg (~34.5 mi), far
    # less than the full ~3.0 deg (~207 mi).
    geom = {"type": "LineString", "coordinates": [[0.5, 0.5], [0.5, 3.5]]}
    full = et._haversine_mi([0.5, 0.5], [0.5, 3.5])
    clipped = et._clipped_miles(geom, SQUARE)
    assert full > 200
    assert 30 < clipped < 40, clipped  # ~0.5 deg inside


def test_clipped_miles_fully_inside_equals_length():
    geom = {"type": "LineString", "coordinates": [[0.2, 0.2], [0.2, 0.8]]}
    full = et._haversine_mi([0.2, 0.2], [0.2, 0.8])
    clipped = et._clipped_miles(geom, SQUARE)
    assert abs(clipped - full) / full < 0.02  # within 2% (sampling granularity)


def test_clipped_miles_fully_outside_is_zero():
    geom = {"type": "LineString", "coordinates": [[5.0, 5.0], [6.0, 6.0]]}
    assert et._clipped_miles(geom, SQUARE) == 0.0


def test_status_colors_distinguish_built_from_planned():
    assert et.STATUS_COLOR["Existing"] != et.STATUS_COLOR["Proposed"]
    assert "Existing" not in et.PLANNED_ORDER
    assert set(et.PLANNED_ORDER) == {"Under Construction", "Programmed", "Proposed"}
