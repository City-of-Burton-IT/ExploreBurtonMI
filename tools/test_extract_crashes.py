# Tests for extract_crashes helpers/config. No network.
# Run: python -m pytest tools/test_extract_crashes.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_crashes as ec  # noqa: E402


def test_yes_is_case_insensitive():
    assert ec._yes("Yes") is True
    assert ec._yes("yes") is True
    assert ec._yes("No") is False
    assert ec._yes(None) is False
    assert ec._yes("Uncoded & Errors") is False


def test_severity_order_and_colors():
    assert ec.SEV_ORDER[0] == "Fatal"  # most severe first
    for s in ec.SEV_ORDER:
        assert s in ec.SEV_COLOR
    assert ec.SEV_COLOR["Fatal"] != ec.SEV_COLOR["Property Damage Only"]


def _traffic(**over):
    t = {"miles_by_band": {"<2k": 10.0, "2k-5k": 5.0, "5k-10k": 3.0, "10k-20k": 2.0, "20k+": 1.5},
         "busiest": [{"name": "S Center Rd", "aadt": 13057, "trucks_pct": 2, "year": 2025}]}
    t.update(over)
    return t


def _panel():
    return {"stats": [], "charts": [], "notes": ["a", "last"], "source": "Crash data."}


def test_merge_traffic_adds_stats_chart_note_source():
    p = _panel()
    ec.merge_traffic(p, _traffic())
    assert [s["label"] for s in p["stats"]] == ["Busiest road counted",
                                                "Miles of road with traffic counts"]
    assert p["stats"][0]["value"] == "S Center Rd" and "13,057" in p["stats"][0]["hint"]
    assert p["stats"][1]["value"] == "21.5" and p["stats"][1]["hint"] == "MDOT 2025 counts"
    ch = p["charts"][0]
    assert ch["title"] == "Road miles by daily traffic" and ch["type"] == "bars"
    assert [x["label"] for x in ch["series"]] == ec.TRAFFIC_BANDS
    assert "residential" in p["notes"][-2] and p["notes"][-1] == "last"
    assert "MDOT" in p["source"] and "OpenStreetMap" in p["source"]
    q = _panel()
    ec.merge_traffic(q, _traffic(mdot_year=2026))
    assert q["stats"][1]["hint"] == "MDOT 2026 counts" and "2026 annual" in q["notes"][-2]


def test_load_traffic_absent_is_none(tmp_path):
    assert ec.load_traffic(str(tmp_path / "nope.json")) is None


def test_load_traffic_valid_and_malformed(tmp_path):
    import json
    import pytest
    good = tmp_path / "t.json"
    good.write_text(json.dumps(_traffic()), encoding="utf-8")
    assert ec.load_traffic(str(good))["busiest"][0]["aadt"] == 13057
    for bad in (_traffic(miles_by_band={"<2k": 1}), _traffic(busiest=[]),
                _traffic(busiest=[{"name": "X", "aadt": "7"}])):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            ec.load_traffic(str(f))
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit):
        ec.load_traffic(str(f))
