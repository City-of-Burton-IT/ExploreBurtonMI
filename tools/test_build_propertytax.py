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

HISTORY = {
    "as_of": "2026-10-07", "from": 2021, "to": 2026,
    "note": "test fixture",
    "years": [
        {"tax_year": 2021, "database": "D004BURTON21",
         "summer": {"due": "2021-09-30", "parcels_billed": 13786, "billed": 27299642, "owed": 1711398,
                    "paid_by_due": 24230848, "paid_within_90": 24972063, "paid_to_date": 25658960},
         "winter": {"due": "2022-02-28", "parcels_billed": 13820, "billed": 10041630, "owed": 1134668,
                    "paid_by_due": 8701210, "paid_within_90": 8884819, "paid_to_date": 8908598}},
        {"tax_year": 2022, "database": "D004BURTON22",
         "summer": {"due": "2022-09-30", "parcels_billed": 13800, "billed": 28411106, "owed": 1500000,
                    "paid_by_due": 25266302, "paid_within_90": 26077678, "paid_to_date": 26660251},
         "winter": {"due": "2023-02-28", "parcels_billed": 13830, "billed": 10200000, "owed": 1100000,
                    "paid_by_due": 8800000, "paid_within_90": 8950000, "paid_to_date": 9000000}},
        {"tax_year": 2023, "database": "D004BURTON23",
         "summer": {"due": "2023-10-02", "parcels_billed": 13850, "billed": 30320886, "owed": 1400000,
                    "paid_by_due": 27360350, "paid_within_90": 28124178, "paid_to_date": 28576469},
         "winter": {"due": "2024-02-29", "parcels_billed": 13860, "billed": 10400000, "owed": 1050000,
                    "paid_by_due": 9000000, "paid_within_90": 9100000, "paid_to_date": 9150000}},
        {"tax_year": 2024, "database": "D004BURTON24",
         "summer": {"due": "2024-09-30", "parcels_billed": 13880, "billed": 31598201, "owed": 1300000,
                    "paid_by_due": 28527361, "paid_within_90": 29236040, "paid_to_date": 29770600},
         "winter": {"due": "2025-02-28", "parcels_billed": 13890, "billed": 10600000, "owed": 1000000,
                    "paid_by_due": 9200000, "paid_within_90": 9300000, "paid_to_date": 9350000}},
        {"tax_year": 2025, "database": "D004BURTON25",
         "summer": {"due": "2025-09-30", "parcels_billed": 13900, "billed": 33987711, "owed": 1250000,
                    "paid_by_due": 30330032, "paid_within_90": 31066223, "paid_to_date": 31600586},
         "winter": {"due": "2026-03-02", "parcels_billed": 13910, "billed": 10800000, "owed": 950000,
                    "paid_by_due": 9500000, "paid_within_90": 9600000, "paid_to_date": 9650000}},
        {"tax_year": 2026, "database": "D004BURTON26",
         "summer": {"due": "2026-09-30", "parcels_billed": 13917, "billed": 35404492, "owed": 3791948,
                    "paid_by_due": 31453310, "paid_within_90": None, "paid_to_date": 31619539},
         "winter": None},
    ],
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


def test_validate_collection_history_accepts_fixture_and_returns_it():
    assert pt.validate_collection_history(copy.deepcopy(HISTORY)) == HISTORY


def test_validate_collection_history_none_passes_through():
    assert pt.validate_collection_history(None) is None


def test_validate_collection_history_rejects_paid_by_due_over_cap():
    bad = copy.deepcopy(HISTORY)
    bad["years"][0]["summer"]["paid_by_due"] = int(bad["years"][0]["summer"]["billed"] * 1.2)
    with pytest.raises(SystemExit):
        pt.validate_collection_history(bad)


def test_validate_collection_history_rejects_within_90_below_paid_by_due():
    bad = copy.deepcopy(HISTORY)
    bad["years"][0]["summer"]["paid_within_90"] = bad["years"][0]["summer"]["paid_by_due"] - 1
    with pytest.raises(SystemExit):
        pt.validate_collection_history(bad)


def test_validate_collection_history_rejects_gap_in_tax_years():
    bad = copy.deepcopy(HISTORY)
    bad["years"][2]["tax_year"] = 2030
    with pytest.raises(SystemExit):
        pt.validate_collection_history(bad)


def test_build_collection_history_chart_shape():
    stats, charts = pt.build_collection_history(copy.deepcopy(HISTORY))
    chart = charts[0]
    assert chart["type"] == "trend"
    assert chart["title"] == "How collections compare, 2021 to 2026"
    assert chart["unit"] == "%"
    labels = [line["label"] for line in chart["lines"]]
    assert labels == [
        "Summer, paid by the due date",
        "Summer, paid within 90 days",
        "Winter, paid by the due date",
    ]
    by_due, within_90, winter = chart["lines"]
    assert len(by_due["points"]) == 6
    assert [p["x"] for p in within_90["points"]] == ["2021", "2022", "2023", "2024", "2025"]
    assert [p["x"] for p in winter["points"]] == ["2021", "2022", "2023", "2024", "2025"]


def test_build_collection_history_stat_format():
    stats, charts = pt.build_collection_history(copy.deepcopy(HISTORY))
    stat = stats[0]
    assert stat["label"] == "Summer levy paid by the due date"
    assert stat["value"] == "89% to 90%"
    assert "2021 to 2025 summers" in stat["hint"]
    assert "2026 came in at" in stat["hint"]
    assert "September 30" in stat["hint"]


def test_build_collection_history_single_value_when_lo_equals_hi():
    flat = copy.deepcopy(HISTORY)
    for y in flat["years"]:
        s = y["summer"]
        s["paid_by_due"] = int(s["billed"] * 0.9)
        if s["paid_within_90"] is not None:
            s["paid_within_90"] = max(s["paid_within_90"], s["paid_by_due"])
    stats, charts = pt.build_collection_history(flat)
    assert stats[0]["value"] == "90%"
