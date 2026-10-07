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


SOURCES = [
    {"fiscal_year_end": y, "scope": sc, "taxes": 3_000_000 + i * 50_000, "licenses_permits": 300_000, "federal": 3_000_000 if y == 2022 else 0,
     "state": 2_500_000 + i * 100_000, "local_units": 0, "charges": 300_000, "fines": 0, "interest": 20_000, "other": 100_000,
     "transfers_in": 0, "unclassified": 0, "total": 6_220_000 + i * 150_000 + (3_000_000 if y == 2022 else 0)}
    for i, y in enumerate(range(2016, 2027)) for sc in ("general_fund", "governmental")
]
DEPTS = []
for y in range(2016, 2027):
    DEPTS += [{"fiscal_year_end": y, "code": "999", "name": "", "amount": 3_000_000},
              {"fiscal_year_end": y, "code": "265", "name": "CITY HALL", "amount": 1_400_000},
              {"fiscal_year_end": y, "code": "448", "name": "PUBLIC SERVICE", "amount": 600_000},
              {"fiscal_year_end": y, "code": "101", "name": "COUNCIL", "amount": 500_000},
              {"fiscal_year_end": y, "code": "257", "name": "ASSESSOR", "amount": 400_000},
              {"fiscal_year_end": y, "code": "171", "name": "MAYOR", "amount": 400_000},
              {"fiscal_year_end": y, "code": "262", "name": "ELECTION", "amount": 300_000},
              {"fiscal_year_end": y, "code": "702", "name": "ZONING", "amount": 80_000}]


def test_revenue_source_chart_and_trend():
    budget = copy.deepcopy(BUDGET)
    budget["revenue_sources"] = SOURCES
    chart = ff.build_revenue_source_chart(budget, "governmental", "governmental funds")
    assert chart["title"] == "Revenue by source, governmental funds, FY2026 ($M, City ledger)"
    labels = [s["label"] for s in chart["series"]]
    assert labels[0] == "Property taxes" and "Federal grants" not in labels   # zero in FY2026
    trend = ff.build_revenue_source_trend(budget)
    assert trend["title"] == "General Fund revenue by source, FY2016–FY2026 ($M)"
    fed = next(ln for ln in trend["lines"] if ln["label"] == "Federal grants")
    assert next(p for p in fed["points"] if p["x"] == "FY2022")["y"] == 3.0
    assert trend["markers"] == [{"x": "FY2022", "label": "American Rescue Plan funds"}]
    assert ff.build_revenue_source_chart(copy.deepcopy(BUDGET), "governmental", "x") is None


def test_department_trend_names_transfers_and_folds_small_departments():
    budget = copy.deepcopy(BUDGET)
    budget["department_history"] = DEPTS
    trend = ff.build_department_trend(budget)
    labels = [ln["label"] for ln in trend["lines"]]
    assert labels[0] == "Transfers to other funds" and labels[1] == "City Hall"
    assert labels[-1] == "All other departments" and len(labels) == ff.DEPT_LINES + 1
    other = trend["lines"][-1]["points"][0]["y"]
    assert other == round((300_000 + 80_000) / 1e6, 2)   # Election + Zoning folded


SPEND_CATEGORY_LABELS = {
    "passthrough": "Taxes collected for schools, the County and the State",
    "water_purchase": "Water bought from the regional system",
    "sewage_treatment": "Sewage treatment by the County",
    "trash": "Trash and recycling pickup",
    "streets": "Street and road projects",
    "utility_projects": "Water and sewer system projects",
    "debt": "Loan and bond payments",
    "insurance_benefits": "Insurance, pensions and employee benefits",
    "utilities": "Utilities and street lighting",
    "vehicles_equipment": "Vehicles, equipment, buildings and parks",
    "services": "Contracted and professional services",
    "supplies": "Supplies and materials",
    "other_operations": "Repairs, rentals, training and other operations",
    "refunds_deposits": "Refunds, deposits returned and other payments",
    "other": "Other",
}

SPEND_CELLS = [
    {"fund": "703", "object": "222", "category": "passthrough", "amount": 18_000_000, "lines": 400},
    {"fund": "591", "object": "816", "category": "water_purchase", "amount": 2_900_000, "lines": 300},
    {"fund": "590", "object": "928", "category": "sewage_treatment", "amount": 2_500_000, "lines": 200},
    {"fund": "226", "object": "830", "category": "trash", "amount": 2_100_000, "lines": 150},
    {"fund": "202", "object": "818", "category": "streets", "amount": 2_000_000, "lines": 180},
    {"fund": "590", "object": "582", "category": "utility_projects", "amount": 1_000_000, "lines": 50},
    {"fund": "591", "object": "300", "category": "debt", "amount": 900_000, "lines": 40},
    {"fund": "101", "object": "231", "category": "insurance_benefits", "amount": 1_600_000, "lines": 90},
    {"fund": "101", "object": "926", "category": "utilities", "amount": 500_000, "lines": 60},
    {"fund": "661", "object": "101", "category": "vehicles_equipment", "amount": 700_000, "lines": 30},
    {"fund": "101", "object": "975", "category": "vehicles_equipment", "amount": 300_000, "lines": 20},
    {"fund": "101", "object": "826", "category": "services", "amount": 1_300_000, "lines": 70},
    {"fund": "101", "object": "740", "category": "supplies", "amount": 600_000, "lines": 50},
    {"fund": "101", "object": "957", "category": "other_operations", "amount": 400_000, "lines": 25},
    {"fund": "101", "object": "285", "category": "refunds_deposits", "amount": 150_000, "lines": 10},
    {"fund": "101", "object": "676", "category": "refunds_deposits", "amount": 50_000, "lines": 5},
    {"fund": "101", "object": "442", "category": "other", "amount": 100_000, "lines": 5},
]

_SPEND_CATEGORIES_NO_PASSTHROUGH = {
    "water_purchase": 2_900_000,
    "sewage_treatment": 2_500_000,
    "trash": 2_100_000,
    "streets": 2_000_000,
    "utility_projects": 1_000_000,
    "debt": 900_000,
    "insurance_benefits": 1_600_000,
    "utilities": 500_000,
    "vehicles_equipment": 1_000_000,
    "services": 1_300_000,
    "supplies": 600_000,
    "other_operations": 400_000,
    "refunds_deposits": 200_000,
    "other": 100_000,
}
_SPEND_CITY_TOTAL = sum(_SPEND_CATEGORIES_NO_PASSTHROUGH.values())
_SPEND_FUND_GROUPS = {
    "General Fund": 1_600_000 + 500_000 + 1_300_000 + 600_000 + 400_000 + 200_000 + 100_000,
    "Streets": 2_000_000,
    "Sewer": 2_500_000 + 1_000_000,
    "Water": 2_900_000 + 900_000,
    "Rubbish": 2_100_000,
    "Motor Pool": 700_000 + 300_000,
}


def _spend_fixture(num_complete_years=9, add_partial=True):
    labels = dict(SPEND_CATEGORY_LABELS)
    base_year = 2017
    years = []
    for i in range(num_complete_years):
        fy = base_year + i
        years.append({
            "fiscal_year": fy, "complete": True,
            "invoices": 5000 + i, "invoice_total": 18_000_000 + _SPEND_CITY_TOTAL,
            "distribution_total": 18_000_000 + _SPEND_CITY_TOTAL,
            "passthrough": 18_000_000, "city_total": _SPEND_CITY_TOTAL,
            "payees": 600 + i, "top10_share": 0.55,
            "categories": dict(_SPEND_CATEGORIES_NO_PASSTHROUGH),
            "fund_groups": dict(_SPEND_FUND_GROUPS),
        })
    latest_complete_fy = years[-1]["fiscal_year"]
    if add_partial:
        partial_fy = latest_complete_fy + 1
        years.append({
            "fiscal_year": partial_fy, "complete": False,
            "invoices": 1200, "invoice_total": 9_000_000 + _SPEND_CITY_TOTAL // 2,
            "distribution_total": 9_000_000 + _SPEND_CITY_TOTAL // 2,
            "passthrough": 9_000_000, "city_total": _SPEND_CITY_TOTAL // 2,
            "payees": 300, "top10_share": 0.5,
            "categories": {k: v // 2 for k, v in _SPEND_CATEGORIES_NO_PASSTHROUGH.items()},
            "fund_groups": {k: v // 2 for k, v in _SPEND_FUND_GROUPS.items()},
        })
    return {
        "_source": "test", "extracted": "2026-10-07", "latest_complete_fy": latest_complete_fy,
        "category_labels": labels,
        "fund_groups": {"101": "General Fund", "202": "Streets", "203": "Streets", "206": "Fire", "207": "Police",
                        "226": "Rubbish", "590": "Sewer", "591": "Water", "661": "Motor Pool", "636": "Information Technology"},
        "street_funds": ["202", "203", "451"], "utility_funds": ["590", "591"],
        "malformed_gl_lines": {"lines": 0, "amount": 0},
        "by_fiscal_year": years,
        "cells": copy.deepcopy(SPEND_CELLS),
    }


SPEND = _spend_fixture()


@pytest.mark.parametrize("fund,obj,expected", [
    ("703", "222", "passthrough"),
    ("591", "816", "water_purchase"),
    ("590", "928", "sewage_treatment"),
    ("226", "830", "trash"),
    ("202", "818", "streets"),
    ("590", "582", "utility_projects"),
    ("591", "300", "debt"),
    ("101", "231", "insurance_benefits"),
    ("101", "926", "utilities"),
    ("661", "101", "vehicles_equipment"),
    ("101", "975", "vehicles_equipment"),
    ("101", "826", "services"),
    ("101", "740", "supplies"),
    ("101", "957", "other_operations"),
    ("101", "285", "refunds_deposits"),
    ("101", "676", "refunds_deposits"),
    ("101", "442", "other"),
])
def test_classify_spend(fund, obj, expected):
    assert ff.classify_spend(fund, obj) == expected


def test_validate_spend_accepts_fixture():
    assert ff.validate_spend(copy.deepcopy(SPEND)) == SPEND


def test_validate_spend_rejects_category_mismatch():
    bad = copy.deepcopy(SPEND)
    bad["by_fiscal_year"][0]["categories"]["other"] += 1_000_000
    with pytest.raises(SystemExit):
        ff.validate_spend(bad)


def test_validate_spend_tolerates_small_rounding_drift():
    # The exporter rounds each category independently, which on a real year can
    # drift the sum a few dollars from the (separately rounded) city_total.
    ok = copy.deepcopy(SPEND)
    ok["by_fiscal_year"][0]["categories"]["other"] += 3
    assert ff.validate_spend(ok) == ok


def test_validate_spend_rejects_too_few_complete_years():
    bad = _spend_fixture(num_complete_years=7, add_partial=False)
    with pytest.raises(SystemExit):
        ff.validate_spend(bad)


def test_validate_spend_rejects_cell_category_disagreement():
    bad = copy.deepcopy(SPEND)
    bad["cells"][0]["category"] = "other"
    with pytest.raises(SystemExit):
        ff.validate_spend(bad)


def test_build_spend_stats_and_charts():
    stats, charts = ff.build_spend(copy.deepcopy(SPEND))
    assert [s["label"] for s in stats] == [
        "Paid to vendors last fiscal year",
        "Collected for other governments",
        "Largest spending category",
        "Paid to the ten largest payees",
    ]
    assert [c["title"] for c in charts] == [
        f"What the City bought, FY{SPEND['latest_complete_fy']} ($M)",
        f"Vendor payments by year, FY{SPEND['by_fiscal_year'][0]['fiscal_year']} to FY{SPEND['latest_complete_fy']} ($M)",
        f"Vendor payments by fund, FY{SPEND['latest_complete_fy']} ($M)",
    ]
    cat_chart = charts[0]
    assert all(s["value"] != 0.0 for s in cat_chart["series"])
    trend = charts[1]
    assert len(trend["lines"]) == 2
    complete_count = sum(1 for r in SPEND["by_fiscal_year"] if r["complete"])
    assert len(trend["lines"][0]["points"]) == complete_count
    assert len(trend["lines"][1]["points"]) == complete_count


def test_history_panel_assembles_sections():
    budget = copy.deepcopy(BUDGET)
    budget["history"] = copy.deepcopy(HISTORY)
    budget["revenue_sources"] = SOURCES
    budget["department_history"] = DEPTS
    audited = [{"type": "trend", "title": "Long-term debt (audited, $M)", "unit": "$M", "points": [{"x": "2024", "y": 30.1}]}]
    panel = ff.build_history_panel(budget, TAXROLL, audited, 2025)
    assert panel["title"] == "City Finances over Time"
    titles = [c["title"] for c in panel["charts"]]
    assert titles[0].startswith("General Fund spending: amended budget vs actual")
    assert "Taxable value by year, City assessment rolls ($M)" in titles
    assert "Taxable value by property class, 2026" not in titles   # donut stays on City Finances
    assert titles[-1] == "Long-term debt (audited, $M)"
    assert [s["label"] for s in panel["stats"]][-1] == "Years the General Fund ended in surplus"
    assert panel["stats"][-1]["value"] == "11 of 11"
