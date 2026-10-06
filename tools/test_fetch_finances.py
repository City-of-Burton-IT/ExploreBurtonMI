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
