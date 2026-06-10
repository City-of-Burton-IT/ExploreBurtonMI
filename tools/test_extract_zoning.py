# Config-consistency tests for extract_zoning. No network.
# Run: python -m pytest tools/test_extract_zoning.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_zoning as ez  # noqa: E402


def test_every_ordered_category_has_a_color():
    for cat in ez.CAT_ORDER:
        assert cat in ez.CAT_COLOR, f"{cat} in CAT_ORDER but missing from CAT_COLOR"


def test_category_colors_are_distinct():
    colors = list(ez.CAT_COLOR.values())
    assert len(colors) == len(set(colors)), "duplicate zoning category colors"
    assert ez.CAT_FALLBACK not in colors  # fallback is reserved for unknowns


def test_round_reduces_precision():
    assert ez._round([[-83.612345678, 43.012345678]]) == [[-83.61235, 43.01235]]
    # nested rings handled recursively
    nested = ez._round([[[-83.6123456, 43.0123456]]])
    assert nested == [[[-83.61235, 43.01235]]]
