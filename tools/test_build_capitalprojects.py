# Tests for build_capitalprojects aggregation + paneling. No network/files.
# Run: python -m pytest tools/test_build_capitalprojects.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_capitalprojects as cp  # noqa: E402


def _raw(**kw):
    base = {"project": "P", "category": "Major Streets", "fund": "Major Streets",
            "funding_source": "Act 51", "fiscal_year": "2027", "amount": "100", "status": "Planned"}
    base.update(kw)
    return base


def test_normalize_buckets_unknown_category_and_funding():
    rows = cp.normalize_rows([_raw(category="Bogus", funding_source="Mystery")])
    assert rows[0]["category"] == "Other"
    assert rows[0]["funding_source"] == "Other"


def test_normalize_clamps_negative_amount_and_bad_status():
    rows = cp.normalize_rows([_raw(amount="-500", status="Whatever")])
    assert rows[0]["amount"] == 0
    assert rows[0]["status"] == "Planned"


def test_aggregate_totals_and_category_breakdown():
    rows = cp.normalize_rows([
        _raw(project="Road A", category="Major Streets", amount="300"),
        _raw(project="Road B", category="Major Streets", amount="200"),
        _raw(project="Truck", category="Facilities & Equipment", amount="500"),
    ])
    agg = cp.aggregate(rows)
    assert agg["total"] == 1000
    assert agg["count"] == 3
    # category totals, largest first
    assert agg["by_category"][0] == ("Facilities & Equipment", 500)
    assert ("Major Streets", 500) in agg["by_category"]


def test_aggregate_funding_and_top_projects_order():
    rows = cp.normalize_rows([
        _raw(project="Big", amount="900", funding_source="Act 51"),
        _raw(project="Mid", amount="400", funding_source="Grant"),
        _raw(project="Small", amount="100", funding_source="Act 51"),
    ])
    agg = cp.aggregate(rows)
    assert agg["by_funding"][0] == ("Act 51", 1000)
    assert [r["project"] for r in agg["top"]] == ["Big", "Mid", "Small"]


def test_trend_shows_multi_year_street_history():
    panel = cp.build_panel(cp.normalize_rows([_raw(fiscal_year="2027")]))
    assert "FY2026-27" in panel["subtitle"]
    trend = next(c for c in panel["charts"] if c["type"] == "trend")
    xs = [p["x"] for p in trend["points"]]
    assert xs == ["FY2024-25", "FY2025-26", "FY2026-27"]   # three years of context


def test_per_resident_stat_present():
    rows = cp.normalize_rows([_raw(amount="2952900")])   # / 29,529 = $100
    panel = cp.build_panel(rows)
    stat = next(s for s in panel["stats"] if s["label"] == "Per resident")
    assert stat["value"] == "$100"


def test_panel_has_required_shape():
    rows = cp.normalize_rows([_raw()])
    panel = cp.build_panel(rows)
    for key in ("title", "subtitle", "summary", "stats", "charts", "tables", "source", "notes"):
        assert key in panel
    assert panel["tables"][0]["columns"][:2] == ["Project", "Category"]
