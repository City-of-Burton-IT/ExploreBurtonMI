"""Unit tests for the Building Permits panel builder (no files, no network)."""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_permits as bp  # noqa: E402


def _cell(count, value=None, with_value=None):
    return {"count": count, "value": count * 10_000 if value is None else value,
            "with_value": count if with_value is None else with_value}


def _row(year, nh=40, hi=500, co=80, dem=20, oth=6):
    row = {"year": year, "total": nh + hi + co + dem + oth,
           "new_homes": _cell(nh), "home_improvements": _cell(hi), "commercial": _cell(co),
           "demolitions": _cell(dem), "other": _cell(oth, 0, 0)}
    return row


def _data():
    rows = [_row(y, nh=30 + y % 7) for y in range(2015, 2027)]
    return {
        "_source": {"server": "S", "database": "D", "table": "dbo.Permits", "note": "aggregates only"},
        "extracted": "2026-10-07",
        "latest_complete_year": 2025,
        "latest_year": next(r for r in rows if r["year"] == 2025),
        "year_to_date": {"as_of": "2026-10-07", "last_permit_issued": "2026-09-28", **rows[-1]},
        "permits_by_year": rows,
        "permits_by_year_all": [{"year": y, "total": 600 + y % 50} for y in range(1999, 2026)],
        "time_to_complete": {"since_year": 2019, "new_homes": {"permits": 300, "median_days": 342},
                             "home_improvements": {"permits": 2800, "median_days": 83}},
        "category_map": [{"category": "ROOFING", "group": "home_improvements", "permits": 5},
                         {"category": "FIREWORKS", "group": "other", "permits": 1}],
    }


@pytest.mark.parametrize("category,group", [
    ("RES, NEW CONSTRUCTION", "new_homes"),
    ("  new house ", "new_homes"),
    ("RES, MODULAR HOME", "new_homes"),
    ("RES, ALTER/REPAIR", "home_improvements"),
    ("ROOFIING", "home_improvements"),
    ("GARAGE, DETACHED", "home_improvements"),
    ("COMMERCIAL, SIGN", "commercial"),
    ("RE-ROOFCOMMERCIAL, ALTER/REPAI", "commercial"),
    ("CELL TOWER", "commercial"),
    ("DEMOLISH", "demolitions"),
    ("DEMO HO", "demolitions"),
    ("FIREWORKS", "other"),
    (None, "other"),
])
def test_classify_category(category, group):
    assert bp.classify_category(category) == group


def test_validate_accepts_good_data():
    assert bp.validate_permits(_data())["latest_complete_year"] == 2025


def test_guard_rejects_too_few_years():
    d = _data()
    d["permits_by_year_all"] = d["permits_by_year_all"][:10]
    with pytest.raises(SystemExit):
        bp.validate_permits(d)


def test_guard_rejects_implausible_counts():
    low = _data()
    low["permits_by_year"][3] = _row(2018, nh=1, hi=10, co=1, dem=1, oth=1)
    with pytest.raises(SystemExit):
        bp.validate_permits(low)
    high = _data()
    high["permits_by_year"][3] = _row(2018, hi=3500)
    with pytest.raises(SystemExit):
        bp.validate_permits(high)
    homes = _data()
    homes["permits_by_year"][10] = _row(2025, nh=400, hi=200)
    with pytest.raises(SystemExit):
        bp.validate_permits(homes)


def test_guard_allows_partial_current_year_below_floor():
    d = _data()
    d["permits_by_year"][-1] = _row(2026, nh=2, hi=40, co=5, dem=1, oth=1)
    assert bp.validate_permits(d)


def test_guard_rejects_category_map_drift():
    d = _data()
    d["category_map"][0]["group"] = "commercial"
    with pytest.raises(SystemExit):
        bp.validate_permits(d)


def test_guard_rejects_group_counts_that_do_not_add_up():
    d = _data()
    d["permits_by_year"][0]["total"] += 5
    with pytest.raises(SystemExit):
        bp.validate_permits(d)


def test_build_panel_stats_and_charts():
    panel = bp.build_panel(bp.validate_permits(_data()))
    labels = [s["label"] for s in panel["stats"]]
    assert labels[:4] == ["Permits issued last year", "New homes permitted last year",
                          "Home-improvement permits last year", "Demolition permits last year"]
    assert panel["stats"][0]["value"] == "638" and "2025" in panel["stats"][0]["hint"]
    assert "Permits so far this year" in labels
    typical = next(s for s in panel["stats"] if s["label"].startswith("Typical time"))
    assert typical["value"] == "83 days" and "11 months" in typical["hint"]
    titles = [c["title"] for c in panel["charts"]]
    assert titles == ["Permits issued per year since 1999", "Permits by type, per year since 2015",
                      "Permits by type, last full year", "New-home permits per year since 2015"]
    assert panel["charts"][0]["points"][-1]["x"] == "2025"
    assert all(p["x"] != "2026" for c in panel["charts"] if "points" in c for p in c["points"])
    assert [s["label"] for s in panel["charts"][2]["series"]][0] == "New homes"
    assert panel["lastUpdated"] == "2026-10"
    assert "Building Department" in panel["source"]


def test_declared_value_shown_only_where_reliable():
    d = _data()
    row = d["permits_by_year"][10]  # 2025
    row["commercial"] = _cell(80, 1_000_000, 20)  # only a quarter stated a value
    panel = bp.build_panel(bp.validate_permits(d))
    hint = next(s for s in panel["stats"] if s["label"].startswith("Stated construction value"))["hint"]
    assert "commercial" not in hint and "new homes" in hint
    for g in ("new_homes", "home_improvements", "commercial", "demolitions"):
        row[g] = _cell(row[g]["count"], 0, 0)
    panel = bp.build_panel(bp.validate_permits(d))
    assert not any(s["label"].startswith("Stated construction value") for s in panel["stats"])
