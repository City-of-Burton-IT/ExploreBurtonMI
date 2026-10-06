# Tests for build_propertytax data integrity. No network; the tax-roll shape is a
# fixture, not the committed file.
# Run: python -m pytest tools/test_build_propertytax.py -q
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_propertytax as pt  # noqa: E402

TAXROLL = {
    "_source": "test",
    "extracted": "2026-10-06",
    "tax_year": 2026,
    "city_mills": 13.2394,
    "city_lines": [
        {"code": "POLICE OP", "mills": 6.3197, "levy": 5_541_907, "parcels": 16571},
        {"code": "UNIT OP", "mills": 4.0, "levy": 3_507_700, "parcels": 16571},
        {"code": "POLICE", "mills": 1.9475, "levy": 1_707_765, "parcels": 16571},
        {"code": "FIRE", "mills": 0.9722, "levy": 852_489, "parcels": 16571},
    ],
    "levy_by_unit": [
        {"code": "POLICE OP", "classification": 7, "season": 0, "mills": 6.3197, "levy": 5_541_907, "parcels": 16571},
        {"code": "SE TAX", "classification": 1, "season": 0, "mills": 6.0, "levy": 5_201_623, "parcels": 16572},
        {"code": "COUNTY OP", "classification": 6, "season": 0, "mills": 5.3003, "levy": 4_647_963, "parcels": 16571},
        {"code": "UNIT OP", "classification": 7, "season": 0, "mills": 4.0, "levy": 3_507_700, "parcels": 16571},
        {"code": "SO TAX", "classification": 2, "season": 0, "mills": 18.0, "levy": 2_898_348, "parcels": 14033},
        {"code": "SPEC ED", "classification": 9, "season": 0, "mills": 2.3103, "levy": 2_025_918, "parcels": 16571},
        {"code": "DDA", "classification": 7, "season": 0, "mills": 1.8673, "levy": 46_090, "parcels": 3606},
        {"code": "MYSTERY", "classification": 12, "season": 0, "mills": 0.1, "levy": 1_000, "parcels": 10},
    ],
    "homestead": {"parcels": 8994, "median_city_tax": 654.84},
}


def test_validate_taxroll_accepts_fixture_and_rejects_bad_sums():
    assert pt.validate_taxroll(copy.deepcopy(TAXROLL)) == TAXROLL
    bad = copy.deepcopy(TAXROLL)
    bad["city_mills"] = 14.0
    with pytest.raises(SystemExit):
        pt.validate_taxroll(bad)
    bad = copy.deepcopy(TAXROLL)
    bad["city_lines"].append({"code": "NEW LEVY", "mills": 0.5, "levy": 1, "parcels": 1})
    bad["city_mills"] = round(bad["city_mills"] + 0.5, 4)
    with pytest.raises(SystemExit):  # unmapped code must be added to CITY_LINE_GROUPS first
        pt.validate_taxroll(bad)


def test_city_levies_group_roll_lines_by_service():
    levies = pt.build_city_levies(TAXROLL)
    assert [lv["id"] for lv in levies] == ["general-operating", "police", "fire"]
    assert [lv["mills"] for lv in levies] == [4.0, 8.2672, 0.9722]
    assert round(sum(lv["mills"] for lv in levies), 4) == TAXROLL["city_mills"]
    assert [lv["voterApproved"] for lv in levies] == [False, True, True]
    assert "2026 tax roll" in levies[1]["description"]


def test_estimator_separates_city_and_complete_bill_periods():
    estimator = pt.build_estimator(TAXROLL)
    assert estimator["cityRatePeriod"] == "2026 tax roll, certified levy"
    assert estimator["fullBillRatePeriod"] == "2025 published rates"
    assert estimator["cityMills"] == 13.2394
    assert estimator["cityLevies"] == pt.build_city_levies(TAXROLL)
    assert "countyMills" not in estimator


def test_levy_chart_groups_units_and_folds_unknown_classifications():
    chart = pt.build_levy_chart(TAXROLL)
    assert chart["type"] == "bars" and chart["title"] == "2026 property tax levy by taxing unit ($M)"
    labels = [s["label"] for s in chart["series"]]
    assert labels[0] == "City of Burton" and labels[-1] == "Other authorities"
    city = next(s for s in chart["series"] if s["label"] == "City of Burton")
    assert city["value"] == round((5_541_907 + 3_507_700 + 46_090) / 1e6, 2)
    assert "Local school district debt" not in labels   # no class-3 line in the fixture


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
