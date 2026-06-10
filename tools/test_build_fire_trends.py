# Tests for build_fire_trends: workbook parsing + idempotent panel merge.
# Parsers are fed synthetic rows via monkeypatch so the tests never touch the
# user's OneDrive workbooks. Run: python -m pytest tools/test_build_fire_trends.py -q
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_fire_trends as bft  # noqa: E402


def test_year_header_maps_years_to_columns():
    assert bft._year_header(("", 2014, 2015, 2016)) == {2014: 1, 2015: 2, 2016: 3}


def test_year_header_ignores_non_years():
    assert bft._year_header(("Label", "x", 99, 2020)) == {2020: 3}


def test_parse_total_by_year(monkeypatch):
    rows = [
        ("", 2014, 2015, 2016),
        ("Structure Fires", 63, 62, 44),
        ("Total Calls for Service", 513, 483, 474),
    ]
    monkeypatch.setattr(bft, "_rows", lambda p: rows)
    assert bft.parse_total_by_year("x") == [
        {"year": 2014, "total": 513},
        {"year": 2015, "total": 483},
        {"year": 2016, "total": 474},
    ]


def test_parse_station_by_year_skips_footer(monkeypatch):
    rows = [
        ("", "YEAR", "STA. #1", "STA. #2", "STA. #3", "Total"),
        ("", 2015, 224, 192, 59, 475),
        ("", 2025, 325, 335, 96, 756),
        ("", "Total:", 8031, 7130, 2451, 17897),   # footer must be ignored
    ]
    monkeypatch.setattr(bft, "_rows", lambda p: rows)
    out = bft.parse_station_by_year("x")
    assert set(out) == {2015, 2025}
    assert out[2025] == [
        ("Station 1 area", 325),
        ("Station 2 area", 335),
        ("Station 3 area", 96),
    ]


def test_parse_category_by_year_maps_labels_and_skips_total(monkeypatch):
    rows = [
        ("", 2015, 2025),
        ("Structure Fires", 62, 63),
        ("Fire & CO Alarm Calls", 82, 174),
        ("Total Calls for Service", 483, 758),   # unrecognized -> skipped
    ]
    monkeypatch.setattr(bft, "_rows", lambda p: rows)
    out = bft.parse_category_by_year("x")
    assert out == {
        "Structure Fires": {2015: 62, 2025: 63},
        "Fire & CO Alarms": {2015: 82, 2025: 174},
    }


def test_baseline_year_prefers_decade_then_earliest():
    assert bft._baseline_year([2014, 2015, 2020, 2025], 2025) == 2015
    assert bft._baseline_year([2020, 2025], 2025) == 2020   # 2015 absent -> earliest


def test_parse_monthly_average_excludes_partial_year(monkeypatch):
    header = ("", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December", "Total")
    rows = [
        header,
        (2024, *([10] * 12), 120),
        (2025, *([20] * 12), 240),
        (2026, 30, 30, 30, *([None] * 9), 90),   # partial -> excluded
        ("AVG.", *([15] * 12), 180),             # non-year label -> skipped
    ]
    monkeypatch.setattr(bft, "_rows", lambda p: rows)
    out = bft.parse_monthly_average("x")
    assert out["years"] == [2024, 2025]
    assert out["avg"] == [15.0] * 12             # (10 + 20) / 2


def _base_panel():
    # The current-year month trend is the EN base chart that survives a merge.
    return {
        "stats": [{"label": "Total responses", "value": "758"}],
        "charts": [{"type": "trend", "title": "Responses by month (2025)"}],
        "notes": ["Aggregates from the City of Burton Fire Department records...",
                  "Draft -- figures pending Fire Department review."],
    }


def test_merge_strips_deprecated_charts():
    # Stale superseded charts from earlier runs must be removed on re-merge:
    # the mutual-aid trend, the NFIRS single-year by-type bars, and the
    # single-year station bars (all replaced by the current chart set).
    panel = _base_panel()
    panel["charts"] += [
        {"type": "trend", "title": "Mutual aid given to neighbors by year (2016-2025)"},
        {"type": "bars", "title": "Responses by type (2025)"},
        {"type": "bars", "title": "Calls by station area (2025)"},
    ]
    out = bft.merge_into_panel(panel, _fragment())
    titles = [c["title"] for c in out["charts"]]
    assert not any(t.startswith("Mutual aid given to neighbors") for t in titles)
    assert not any(t.startswith("Responses by type (") for t in titles)
    assert not any(t.startswith("Calls by station area (") for t in titles)
    # the current-year month trend (not deprecated) is preserved
    assert "Responses by type (2025)" not in titles


def _fragment():
    return {
        "charts": [{"type": "trend",
                    "title": "Total calls for service by year (2014-2025)",
                    "points": [{"x": "2014", "y": 513}]}],
        "stats": [{"label": "11-year change", "value": "+48%"}],
        "notes": [bft.HISTORY_MARK + " workbooks, maintained by the Chief's office."],
    }


def test_merge_is_idempotent():
    once = bft.merge_into_panel(_base_panel(), _fragment())
    twice = bft.merge_into_panel(once, _fragment())
    assert once == twice
    titles = [c["title"] for c in twice["charts"]]
    assert titles.count("Total calls for service by year (2014-2025)") == 1
    labels = [s["label"] for s in twice["stats"]]
    assert labels.count("11-year change") == 1


def test_merge_keeps_existing_charts_and_draft_note_last():
    out = bft.merge_into_panel(_base_panel(), _fragment())
    assert out["charts"][0]["title"] == "Responses by month (2025)"  # base preserved
    assert out["charts"][-1]["title"].startswith("Total calls")      # trend appended
    assert out["notes"][-1].startswith("Draft")                      # draft stays last
    assert any(n.startswith(bft.HISTORY_MARK) for n in out["notes"])


def test_merge_output_is_json_serializable():
    out = bft.merge_into_panel(_base_panel(), _fragment())
    json.dumps(out)  # must not raise
