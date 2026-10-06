"""Unit tests for the Water & Sewer Funds panel builder (no files, no network)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_utilities as bu  # noqa: E402


def _row(fund, fy, usage, other, treat, ops, dep, debt):
    return {"fiscal_year_end": fy, "fund": fund, "usage_fees": usage, "other_revenue": other,
            "treatment_purchase": treat, "operations": ops, "depreciation": dep, "debt_and_transfers": debt}


ENTERPRISE = []
for i, fy in enumerate(range(2016, 2027)):
    ENTERPRISE.append(_row("591", fy, 4_800_000 + i * 230_000, 900_000, 3_000_000 + i * 110_000, 1_200_000, 600_000, 250_000))
    ENTERPRISE.append(_row("590", fy, 5_600_000 + i * 110_000, 1_000_000, 3_400_000 + i * 80_000, 900_000, 700_000, 180_000))

UTILITY = {"customers_residential": 11242, "customers_commercial": 890, "accounts_sewer_only": 5058,
           "median_annual_water_sewer": 974, "median_annual_sewer_only": 545}


def test_panel_stats_and_charts():
    panel = bu.build_panel(ENTERPRISE, UTILITY, "2026-10-06")
    labels = [s["label"] for s in panel["stats"]]
    assert labels == ["Water fund: bills collected, FY2026", "Sewer fund: bills collected, FY2026",
                      "Customer accounts", "Typical water and sewer bill"]
    assert panel["stats"][0]["value"] == "$7.1M" and "purchased water" in panel["stats"][0]["hint"]
    assert panel["stats"][2]["value"] == "11,242" and "890" in panel["stats"][2]["hint"]
    titles = [c["title"] for c in panel["charts"]]
    assert titles[0] == "Water fund: revenue and spending by year, FY2016–FY2026 ($M)"
    assert titles[2] == "Where the water dollar went, FY2026"
    assert titles[-1].startswith("Cost of purchased water and sewage treatment by year")
    water_trend = panel["charts"][0]
    assert [ln["label"] for ln in water_trend["lines"]] == ["Revenue (bills and other)", "Spending"]
    assert water_trend["lines"][0]["points"][-1] == {"x": "FY2026", "y": 8.0}
    donut = panel["charts"][2]
    assert donut["series"][0] == {"label": "Purchased water", "value": 4.1}
    sewer_donut = panel["charts"][3]
    assert sewer_donut["series"][0]["label"] == "Sewage treatment"
    assert "enterprise funds" in panel["source"].lower() or "Water (591)" in panel["source"]


def test_panel_without_utility_block_omits_customer_stats():
    panel = bu.build_panel(ENTERPRISE, None, "2026-10-06")
    assert len(panel["stats"]) == 2
    assert "Utility Billing" not in panel["source"]


def test_validate_enterprise_rejects_bad_rows():
    bad = [dict(r) for r in ENTERPRISE]
    bad[0]["fund"] = "101"
    with pytest.raises(SystemExit):
        bu.validate_enterprise(bad)
    with pytest.raises(SystemExit):
        bu.validate_enterprise(ENTERPRISE[:4])
    assert bu.validate_enterprise(ENTERPRISE) == ENTERPRISE
