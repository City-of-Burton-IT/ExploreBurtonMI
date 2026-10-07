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


def _insp_year(year, completed=1000, approved=800, disapproved=150, partially_approved=40,
               not_ready=5, locked_out=2, canceled=3, none=0):
    return {"year": year, "completed": completed, "approved": approved, "disapproved": disapproved,
            "partially_approved": partially_approved, "not_ready": not_ready, "locked_out": locked_out,
            "canceled": canceled, "none": none}


def _status_group(permits, finaled=0, closed=0, expired=0, open_=0, canceled=0, other=0):
    return {"permits": permits, "finaled": finaled, "closed": closed, "expired": expired,
            "open": open_, "canceled": canceled, "other": other}


def _permits_year(year, building=300, site=150, other=10):
    return {
        "year": year, "permits": building + site + other,
        "building": _status_group(building, finaled=building - 10, closed=5, expired=5),
        "site": _status_group(site, finaled=site - 5, closed=5),
        "other": _status_group(other, finaled=other),
    }


def _workflow():
    insp_years = [_insp_year(y, completed=1000 + y, approved=800 + y, disapproved=150, partially_approved=40)
                  for y in range(2019, 2025)]
    insp_years.append(_insp_year(2025, completed=1424, approved=1187, disapproved=151, partially_approved=63,
                                  not_ready=7, locked_out=0, canceled=16, none=0))
    insp_years.append(_insp_year(2026, completed=700, approved=550, disapproved=100, partially_approved=30,
                                  not_ready=10, locked_out=5, canceled=5, none=0))
    return {
        "_source": {"server": "S", "database": "D", "tables": "dbo.Permit, dbo.Inspection",
                    "note": "aggregates only"},
        "extracted": "2026-10-07",
        "latest_complete_year": 2025,
        "status_codes": {"0": "Unknown", "1": "Issued", "6": "Finaled", "7": "Expired", "14": "Closed"},
        "result_codes": {"0": "None", "1": "Approved", "2": "Disapproved", "3": "Partially Approved",
                          "4": "Not Ready", "5": "Locked Out", "6": "Canceled"},
        "inspections_by_year": insp_years,
        "inspection_types_latest": {"year": 2025, "minimum_count": 25, "types": [
            {"type": "FINAL", "completed": 772, "approved": 690, "disapproved": 58, "partially_approved": 17},
            {"type": "FRAMING", "completed": 200, "approved": 145, "disapproved": 48, "partially_approved": 3},
            {"type": "FOOTING", "completed": 128, "approved": 113, "disapproved": 8, "partially_approved": 2},
        ]},
        "permits_by_issue_year": [_permits_year(y) for y in range(2019, 2027)],
        "finished_within_year": {"permit_type": "Building", "through_year": 2024, "years": [
            {"year": 2019, "permits": 457, "finaled_within_year": 306, "finaled_ever": 373},
            {"year": 2020, "permits": 361, "finaled_within_year": 230, "finaled_ever": 299},
            {"year": 2021, "permits": 373, "finaled_within_year": 195, "finaled_ever": 309},
            {"year": 2022, "permits": 303, "finaled_within_year": 207, "finaled_ever": 265},
            {"year": 2023, "permits": 335, "finaled_within_year": 261, "finaled_ever": 312},
        ]},
        "inspections_per_permit": {"year": 2025, "permit_type": "Building", "permits": 418, "inspections": 969},
    }


def test_validate_workflow_accepts_good_data():
    assert bp.validate_workflow(_workflow())["latest_complete_year"] == 2025


def test_validate_workflow_rejects_changed_decode():
    wf = _workflow()
    wf["status_codes"]["6"] = "Done"
    with pytest.raises(SystemExit):
        bp.validate_workflow(wf)


def test_validate_workflow_rejects_low_pass_rate():
    wf = _workflow()
    wf["inspections_by_year"][0] = _insp_year(2019, completed=1000, approved=400, disapproved=550,
                                               partially_approved=50)
    with pytest.raises(SystemExit):
        bp.validate_workflow(wf)


def test_validate_workflow_rejects_group_counts_that_do_not_add_up():
    wf = _workflow()
    wf["permits_by_issue_year"][0]["building"]["permits"] += 5
    with pytest.raises(SystemExit):
        bp.validate_workflow(wf)


def test_validate_workflow_rejects_finaled_within_year_over_ever():
    wf = _workflow()
    wf["finished_within_year"]["years"][0]["finaled_within_year"] = (
        wf["finished_within_year"]["years"][0]["finaled_ever"] + 1)
    with pytest.raises(SystemExit):
        bp.validate_workflow(wf)


def test_build_workflow_stats_and_charts():
    wf = bp.validate_workflow(_workflow())
    stats, charts = bp.build_workflow(wf)
    labels = [s["label"] for s in stats]
    assert labels == ["Inspections completed last year", "Inspections passed last year",
                       "Projects finished within a year", "Inspections per building permit"]
    titles = [c["title"] for c in charts]
    assert titles == ["Inspection results per year since 2019",
                       "Building permits finished within a year of issue, 2019 to 2024",
                       "Inspections completed by type, 2025"]
    first_chart_years = [p["x"] for p in charts[0]["lines"][0]["points"]]
    assert "2026" not in first_chart_years


def test_build_panel_without_workflow_keeps_original_charts():
    panel = bp.build_panel(bp.validate_permits(_data()))
    titles = [c["title"] for c in panel["charts"]]
    assert titles == ["Permits issued per year since 1999", "Permits by type, per year since 2015",
                      "Permits by type, last full year", "New-home permits per year since 2015"]


def test_build_panel_with_workflow_appends_stats_charts_and_notes():
    wf = bp.validate_workflow(_workflow())
    panel = bp.build_panel(bp.validate_permits(_data()), wf)
    titles = [c["title"] for c in panel["charts"]]
    assert "Inspection results per year since 2019" in titles
    assert "Building permits finished within a year of issue, 2019 to 2024" in titles
    assert "Inspections completed by type, 2025" in titles
    assert any("application" in n and "issue" in n for n in panel["notes"])
    assert any("twelve months" in n for n in panel["notes"])


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
