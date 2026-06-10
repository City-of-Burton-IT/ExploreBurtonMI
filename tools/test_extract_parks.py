# Unit tests for extract_parks pure functions. No network.
# Run: python -m pytest tools/test_extract_parks.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_parks as ep  # noqa: E402

SQUARE = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]


def test_category_from_type_or_owner():
    assert ep._category("City of Burton Park", "City of Burton") == "City of Burton"
    assert ep._category("County Park", "Genesee County Parks") == "Genesee County"
    assert ep._category("Neighborhood Park", "") == "Neighborhood"
    assert ep._category("Regional", "Some Township") == "Other"
    # Burton wins even if also tagged county/neighborhood text.
    assert ep._category("Neighborhood Park", "City of Burton") == "City of Burton"


def test_every_category_has_color():
    for c in ep.CAT_ORDER:
        assert c in ep.CAT_COLOR


def test_centroid_polygon():
    poly = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    c = ep._centroid(poly)
    # mean of the 5 vertices (closing vertex repeats 0,0) -> (0.8, 0.8)
    assert round(c[0], 3) == 0.8 and round(c[1], 3) == 0.8


def test_centroid_inside_square():
    poly = {"type": "Polygon", "coordinates": [[[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6], [0.4, 0.4]]]}
    c = ep._centroid(poly)
    assert ep._inside(c[0], c[1], SQUARE) is True
    far = {"type": "Polygon", "coordinates": [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]]}
    fc = ep._centroid(far)
    assert ep._inside(fc[0], fc[1], SQUARE) is False
