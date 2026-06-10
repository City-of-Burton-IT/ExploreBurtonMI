# Tests for extract_access pure helpers. No network.
# Run: python -m pytest tools/test_extract_access.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_access as ea  # noqa: E402

SQUARE = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]


def test_num_parses_percent_and_commas():
    assert ea._num("97.70%") == 97.7
    assert ea._num("53,945") == 53945.0
    assert ea._num("") is None
    assert ea._num(None) is None
    assert ea._num("n/a") is None


def test_median():
    assert ea._median([1, 2, 3]) == 2
    assert ea._median([1, 2, 3, 4]) == 2.5
    assert ea._median([]) is None


def test_avg_ignores_none_and_zero():
    rows = [{"x": 10}, {"x": 20}, {"x": 0}, {"x": None}, {"x": ""}]
    assert ea._avg(rows, "x") == 15.0  # only 10 and 20 count


def test_burton_areas_filters_by_interior_point():
    rows = [
        {"INTPTLON20": "0.5", "INTPTLAT20": "0.5", "v": "in"},
        {"INTPTLON20": "5.0", "INTPTLAT20": "5.0", "v": "out"},
        {"INTPTLON20": "bad", "INTPTLAT20": "bad", "v": "skip"},
    ]
    kept = ea._burton_areas(rows, SQUARE)
    assert [r["v"] for r in kept] == ["in"]
