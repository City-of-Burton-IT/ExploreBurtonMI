# Tests for build_propertytax data integrity. No network/files.
# Run: python -m pytest tools/test_build_propertytax.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_propertytax as pt  # noqa: E402


def test_provisional_city_rate_uses_last_supported_rate_pending_l4029():
    assert pt.CITY_TOTAL == 13.44
    assert f"{pt.CITY_TOTAL:.1f}" == "13.4"


def test_budget_service_breakdown_reconciles_to_provisional_total():
    assert pt.CITY_GENERAL == 4.0000
    assert pt.CITY_POLICE == 8.3159
    assert pt.CITY_FIRE == 0.9789
    assert pt.BUDGET_SERVICE_TOTAL == 13.2948
    assert pt.RECONCILIATION_DIFFERENCE == 0.1452
    assert [levy["id"] for levy in pt.CITY_LEVIES] == [
        "general-operating",
        "police",
        "fire",
        "l4029-reconciliation",
    ]
    assert [levy["mills"] for levy in pt.CITY_LEVIES] == [
        4.0000,
        8.3159,
        0.9789,
        0.1452,
    ]
    assert pt.CITY_LEVIES[-1]["service"] == "Unassigned difference"
    assert pt.CITY_LEVIES[-1]["authorization"] == "Pending L-4029"
    assert round(sum(levy["mills"] for levy in pt.CITY_LEVIES), 4) == pt.CITY_TOTAL
    assert round(
        sum(levy["mills"] for levy in pt.CITY_LEVIES if levy["voterApproved"]),
        4,
    ) == 9.2948


def test_estimator_separates_city_and_complete_bill_periods():
    estimator = pt.build_estimator()
    assert estimator["cityRatePeriod"] == "Provisional — current L-4029 pending"
    assert estimator["fullBillRatePeriod"] == "2025 published rates"
    assert estimator["cityMills"] == 13.44
    assert estimator["cityLevies"] == pt.CITY_LEVIES
    assert "countyMills" not in estimator


def test_breakdown_note_says_budget_rows_are_shown():
    assert "are shown as budget-reference rows" in pt.BREAKDOWN_NOTE
    assert "are not shown as budget-reference rows" not in pt.BREAKDOWN_NOTE


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
