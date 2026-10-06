"""Unit tests for the GL-driven adopted-budget pieces of the finance panel (no network)."""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fetch_finances as ff  # noqa: E402

BUDGET = {
    "_source": "test",
    "extracted": "2026-10-06",
    "fiscal_year_end": 2027,
    "label": "FY2026-27",
    "totals": {"revenue": 51_000_000, "expenditure": 63_000_000, "transfers_out": 3_000_000},
    "funds": [
        {"fund": "202", "name": "MAJOR STREETS", "revenue": 4_800_000, "expenditure": 13_000_000, "transfers_out": 0},
        {"fund": "207", "name": "POLICE FUND", "revenue": 9_000_000, "expenditure": 10_000_000, "transfers_out": 0},
        {"fund": "101", "name": "GENERAL FUND", "revenue": 8_850_000, "expenditure": 10_000_000, "transfers_out": 3_000_000},
        {"fund": "591", "name": "WATER DEPARTMENT", "revenue": 7_900_000, "expenditure": 8_000_000, "transfers_out": 0},
        {"fund": "590", "name": "SEWER FUND", "revenue": 7_600_000, "expenditure": 7_000_000, "transfers_out": 0},
        {"fund": "203", "name": "LOCAL STREETS", "revenue": 1_900_000, "expenditure": 4_000_000, "transfers_out": 0},
        {"fund": "677", "name": "BURTON SELF INSURANCE FUND", "revenue": 2_400_000, "expenditure": 2_400_000, "transfers_out": 0},
        {"fund": "206", "name": "FIRE DEPARTMENT", "revenue": 1_800_000, "expenditure": 2_200_000, "transfers_out": 0},
        {"fund": "226", "name": "RUBBISH COLLECTION & DISPOSAL", "revenue": 2_100_000, "expenditure": 2_100_000, "transfers_out": 0},
        {"fund": "661", "name": "MOTOR POOL", "revenue": 2_300_000, "expenditure": 1_500_000, "transfers_out": 0},
        {"fund": "636", "name": "INFORMATION TECHNOLOGY FUND", "revenue": 750_000, "expenditure": 750_000, "transfers_out": 0},
        {"fund": "279", "name": "SENIOR CITIZENS CENTER FUND", "revenue": 570_000, "expenditure": 650_000, "transfers_out": 0},
        {"fund": "249", "name": "BUILDING DEPARTMENT FUND", "revenue": 530_000, "expenditure": 500_000, "transfers_out": 0},
        {"fund": "273", "name": "VETERAN'S MEMORIAL PARK FUND", "revenue": 5_000, "expenditure": 600_000, "transfers_out": 0},
        {"fund": "284", "name": "OPIOID SETTLEMENT FUND", "revenue": 2_500, "expenditure": 300_000, "transfers_out": 0},
    ],
    "general_fund": {
        "revenue": 8_850_000, "expenditure": 10_000_000, "transfers_out": 3_000_000,
        "departments": [
            {"code": "999", "name": "", "amount": 3_000_000},
            {"code": "265", "name": "CITY HALL", "amount": 1_700_000},
            {"code": "101", "name": "COUNCIL", "amount": 1_000_000},
            {"code": "751", "name": "PARKS & RECREATION", "amount": 900_000},
            {"code": "448", "name": "PUBLIC SERVICE", "amount": 700_000},
            {"code": "257", "name": "ASSESSOR", "amount": 630_000},
            {"code": "262", "name": "ELECTION", "amount": 580_000},
            {"code": "171", "name": "MAYOR", "amount": 500_000},
            {"code": "215", "name": "CLERK", "amount": 350_000},
            {"code": "191", "name": "CONTROLLER", "amount": 340_000},
            {"code": "253", "name": "TREASURER", "amount": 160_000},
            {"code": "701", "name": "PLANNING", "amount": 90_000},
            {"code": "702", "name": "ZONING", "amount": 50_000},
        ],
        "transfers": [
            {"account": "995.661", "name": "TRANSFER TO MOTOR POOL", "amount": 1_000_000},
            {"account": "995.206", "name": "TRANSFER TO FIRE DEPARTMENT FUND", "amount": 800_000},
            {"account": "995.207", "name": "TRANSFER TO POLICE FUND", "amount": 500_000},
            {"account": "995.279", "name": "TRANSFER TO SENIOR CITIZENS FUND", "amount": 300_000},
            {"account": "995.203", "name": "TRANSFER TO LOCAL STREETS", "amount": 250_000},
            {"account": "995.202", "name": "TRANSFER TO MAJOR STREETS", "amount": 150_000},
        ],
    },
}


def test_budget_stats_come_from_the_ledger_totals():
    stats = ff.build_budget_stats(BUDGET)
    assert [s["label"] for s in stats] == ["Total budget", "General Fund budget"]
    assert stats[0]["value"] == "$63.0M" and "General Ledger" in stats[0]["hint"]
    assert stats[1]["value"] == "$10.0M" and "$3.0M in transfers" in stats[1]["hint"]


def test_fund_chart_shares_sum_to_total_and_fold_small_funds():
    bars, _ = ff.build_budget_charts(BUDGET)
    assert bars["type"] == "bars" and bars["title"] == "FY2026-27 adopted budget by fund (all funds)"
    labels = [s["label"] for s in bars["series"]]
    assert labels[0] == "Major Streets" and labels[1] == "Police Fund"
    assert labels[-1] == "All other funds"
    assert len(bars["series"]) == ff.FUND_CHART_SLICES + 1
    assert abs(sum(s["value"] for s in bars["series"]) - 100) < 0.5
    assert bars["series"][0]["value"] == round(100 * 13_000_000 / 63_000_000, 1)


def test_general_fund_mix_expands_transfers_and_titles_departments():
    _, donut = ff.build_budget_charts(BUDGET)
    assert donut["type"] == "donut" and donut["title"] == "General Fund spending mix, FY2026-27 (plan)"
    labels = [s["label"] for s in donut["series"]]
    assert "City Hall" in labels and "Parks & Recreation" in labels
    assert "Transfer to Motor Pool" in labels and "Transfer to Fire Department Fund" in labels
    assert "Other departments and transfers" in labels   # small departments and transfers fold together
    assert not any(lbl.isupper() for lbl in labels)
    assert abs(sum(s["value"] for s in donut["series"]) - 100) < 0.5
    assert len(donut["series"]) <= ff.GF_MIX_SLICES + 1


def test_validate_budget_rejects_inconsistent_totals():
    bad = copy.deepcopy(BUDGET)
    bad["totals"]["expenditure"] = 1
    with pytest.raises(SystemExit):
        ff.validate_budget(bad)
    bad = copy.deepcopy(BUDGET)
    bad["general_fund"]["departments"][0]["amount"] = 5
    with pytest.raises(SystemExit):
        ff.validate_budget(bad)
    bad = copy.deepcopy(BUDGET)
    del bad["funds"]
    with pytest.raises(SystemExit):
        ff.validate_budget(bad)
    assert ff.validate_budget(copy.deepcopy(BUDGET)) == BUDGET


def test_title_case_keeps_short_acronyms():
    assert ff._title("PARKS & RECREATION") == "Parks & Recreation"
    assert ff._title("INFORMATION TECHNOLOGY FUND") == "Information Technology Fund"
    assert ff._title("POLICE K9 FUND") == "Police K9 Fund"


ACTUALS = {
    "prior_year": {
        "fiscal_year_end": 2026, "label": "FY2025-26",
        "funds": [
            {"fund": "202", "name": "MAJOR STREETS", "revenue_budget": 6_455_550, "expenditure_budget": 12_920_873,
             "revenue_actual": 6_644_277, "expenditure_actual": 6_403_297},
            {"fund": "101", "name": "GENERAL FUND", "revenue_budget": 8_806_658, "expenditure_budget": 11_888_730,
             "revenue_actual": 8_682_427, "expenditure_actual": 10_780_128},
            {"fund": "207", "name": "POLICE FUND", "revenue_budget": 8_154_973, "expenditure_budget": 9_606_819,
             "revenue_actual": 8_585_574, "expenditure_actual": 8_559_172},
        ],
    },
    "year_to_date": {
        "fiscal_year_end": 2027, "through": "2026-09-30", "through_label": "September 2026", "months": 3,
        "funds": [{"fund": "101", "revenue_actual": 3_957_438, "expenditure_actual": 1_103_015}],
    },
}

TAXROLL = {
    "_source": "test", "extracted": "2026-10-06", "tax_year": 2026,
    "taxable_value": {
        "year": 2026, "total": 895_540_516, "sev": 1_293_714_100,
        "by_group": [
            {"group": "Residential", "parcels": 12703, "taxable": 605_042_919, "sev": 951_286_900},
            {"group": "Commercial", "parcels": 721, "taxable": 159_558_091, "sev": 200_000_000},
            {"group": "Personal property (business and utility)", "parcels": 243, "taxable": 75_349_400, "sev": 80_000_000},
            {"group": "Industrial", "parcels": 206, "taxable": 55_590_106, "sev": 62_427_200},
        ],
        "history": [{"year": 2024, "taxable": 813_987_953, "sev": 1_174_609_300},
                    {"year": 2025, "taxable": 857_669_350, "sev": 1_228_031_600},
                    {"year": 2026, "taxable": 895_540_516, "sev": 1_293_714_100}],
    },
}


def test_actuals_stats_and_charts():
    budget = copy.deepcopy(BUDGET)
    budget["actuals"] = ACTUALS
    assert ff.validate_budget(copy.deepcopy(budget)) == budget
    stats, charts = ff.build_actuals(budget)
    assert [s["label"] for s in stats] == ["General Fund result, FY2025-26", "General Fund spending so far"]
    assert stats[0]["value"] == "-$2.1M" and "reserves" in stats[0]["hint"]
    assert stats[1]["value"] == "11% of plan" and "September 2026" in stats[1]["hint"] and "25% of the year" in stats[1]["hint"]
    assert [c["title"] for c in charts] == [
        "General Fund, FY2025-26: budget vs actual ($M)", "Spending by fund, FY2025-26: budget vs actual ($M)",
    ]
    gf = charts[0]["rows"]
    assert gf[0]["values"] == [{"name": "Budget", "value": 8.81}, {"name": "Actual", "value": 8.68}]
    assert gf[1]["values"] == [{"name": "Budget", "value": 11.89}, {"name": "Actual", "value": 10.78}]
    assert [r["label"] for r in charts[1]["rows"]] == ["Major Streets", "General Fund", "Police Fund"]


def test_actuals_absent_yields_nothing():
    assert ff.build_actuals(copy.deepcopy(BUDGET)) == ([], [])


def test_taxable_value_stat_and_charts():
    assert ff.validate_taxroll(copy.deepcopy(TAXROLL)) == TAXROLL
    stats, charts = ff.build_taxable_value(TAXROLL)
    assert stats == [{"label": "Taxable value", "value": "$895.5M", "hint": "2026 assessment roll, City Assessor (BS&A)"}]
    assert charts[0]["title"] == "Taxable value by year, City assessment rolls ($M)"
    assert charts[0]["points"][-1] == {"x": "2026", "y": 895.5}
    assert charts[1]["type"] == "donut" and charts[1]["series"][0] == {"label": "Residential", "value": 605.0}


def test_validate_taxroll_rejects_mismatched_groups():
    bad = copy.deepcopy(TAXROLL)
    bad["taxable_value"]["by_group"][0]["taxable"] = 1
    with pytest.raises(SystemExit):
        ff.validate_taxroll(bad)


HISTORY = [
    {"fiscal_year_end": y,
     "general_fund": {"revenue_actual": 6_000_000 + i * 100_000, "expenditure_actual": 5_900_000 + i * 100_000,
                      "revenue_amended": 6_100_000 + i * 100_000, "expenditure_amended": 6_200_000 + i * 100_000},
     "all_funds": {"revenue_actual": 30_000_000 + i * 1_000_000, "expenditure_actual": 29_000_000 + i * 1_000_000,
                   "expenditure_amended": 31_000_000 + i * 1_000_000}}
    for i, y in enumerate(range(2016, 2027))
]


def test_history_charts_span_years_and_mark_known_events():
    budget = copy.deepcopy(BUDGET)
    budget["history"] = copy.deepcopy(HISTORY)
    assert ff.validate_budget(copy.deepcopy(budget)) == budget
    charts = ff.build_history_charts(budget)
    assert [c["title"] for c in charts] == [
        "General Fund spending: amended budget vs actual, FY2016–FY2026 ($M)",
        "General Fund revenue: amended budget vs actual, FY2016–FY2026 ($M)",
        "All City funds: revenue and spending by year, FY2016–FY2026 ($M)",
    ]
    assert [ln["label"] for ln in charts[0]["lines"]] == ["Amended budget", "Actual"]
    assert charts[0]["lines"][1]["points"][0] == {"x": "FY2016", "y": 5.9}
    assert charts[0]["lines"][1]["points"][-1] == {"x": "FY2026", "y": 6.9}
    assert charts[2]["markers"] == [m for m in ff.HISTORY_MARKERS if m["x"] == "FY2018"]
    assert ff.build_history_charts(copy.deepcopy(BUDGET)) == []


def test_validate_budget_rejects_bad_history():
    bad = copy.deepcopy(BUDGET)
    bad["history"] = copy.deepcopy(HISTORY)
    bad["history"][3]["general_fund"]["revenue_actual"] = "x"
    with pytest.raises(SystemExit):
        ff.validate_budget(bad)
    bad = copy.deepcopy(BUDGET)
    bad["history"] = list(reversed(copy.deepcopy(HISTORY)))
    with pytest.raises(SystemExit):
        ff.validate_budget(bad)
