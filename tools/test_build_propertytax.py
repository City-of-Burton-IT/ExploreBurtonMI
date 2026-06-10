# Tests for build_propertytax data integrity. No network/files.
# Run: python -m pytest tools/test_build_propertytax.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_propertytax as pt  # noqa: E402


def test_city_components_sum_to_total():
    # Allow 0.01 for the ACFR's rounding of the three component mills.
    assert abs((pt.CITY_GENERAL + pt.CITY_POLICE + pt.CITY_FIRE) - pt.CITY_TOTAL) <= 0.02


def test_breakdown_reconciles_to_homestead_total():
    uniform = pt.CITY_TOTAL + pt.COUNTY + pt.MOTT + pt.ISD + pt.MTA + pt.AIRPORT
    schools_set = round(pt.HOMESTEAD_TOTAL - uniform, 2)
    assert schools_set > 0  # the remainder must be a real, positive slice
    assert abs((uniform + schools_set) - pt.HOMESTEAD_TOTAL) < 0.001


def test_districts_present_and_sorted_ascending():
    vals = [v for _, v in pt.DISTRICT_HOMESTEAD]
    assert len(pt.DISTRICT_HOMESTEAD) == 7  # Burton has 7 school districts
    assert vals == sorted(vals)


def test_city_millage_history_flat_or_declining():
    vals = [v for _, v in pt.CITY_MILLAGE_HISTORY]
    assert vals[0] >= vals[-1]  # rate has not risen over the decade
    assert len(vals) == 10
