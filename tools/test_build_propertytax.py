# Tests for build_propertytax data integrity. No network/files.
# Run: python -m pytest tools/test_build_propertytax.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_propertytax as pt  # noqa: E402


def test_fy2026_27_city_levies_match_adopted_budget():
    assert pt.CITY_GENERAL == 4.0000
    assert pt.CITY_POLICE == 8.3159
    assert pt.CITY_FIRE == 0.9789
    assert pt.CITY_TOTAL == 13.2948
    assert pt.VOTER_APPROVED_TOTAL == 9.2948


def test_city_levies_have_unique_ids_and_exact_authorization():
    assert len({levy["id"] for levy in pt.CITY_LEVIES}) == 3
    assert [levy["authorization"] for levy in pt.CITY_LEVIES] == [
        "City Charter",
        "Voter approved",
        "Voter approved",
    ]
    assert round(sum(levy["mills"] for levy in pt.CITY_LEVIES), 4) == pt.CITY_TOTAL
    assert round(
        sum(levy["mills"] for levy in pt.CITY_LEVIES if levy["voterApproved"]),
        4,
    ) == pt.VOTER_APPROVED_TOTAL


def test_estimator_separates_city_and_complete_bill_periods():
    estimator = pt.build_estimator()
    assert estimator["cityRatePeriod"] == "FY2026-27 adopted levy"
    assert estimator["fullBillRatePeriod"] == "2025 published rates"
    assert estimator["cityMills"] == 13.2948
    assert estimator["cityLevies"] == pt.CITY_LEVIES
    assert "countyMills" not in estimator


def test_breakdown_reconciles_to_homestead_total():
    assert pt.PUBLISHED_2025_CITY_TOTAL == 13.44
    uniform = (
        pt.PUBLISHED_2025_CITY_TOTAL
        + pt.COUNTY
        + pt.MOTT
        + pt.ISD
        + pt.MTA
        + pt.AIRPORT
    )
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
