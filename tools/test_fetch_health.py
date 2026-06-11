"""Unit tests for the Community Health cities-ranking builder (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fetch_health as fh  # noqa: E402


def _row(**kw):
    """A fake CDC PLACES place row: each measure as a `<code>_crudeprev` string."""
    return {f"{k}_crudeprev": str(v) for k, v in kw.items()}


def test_city_rankings_sorted_desc_with_burton():
    city_rows = {
        "Burton": _row(access2=8.1, obesity=40.8, csmoking=20, diabetes=12, bphigh=38),
        "Flint": _row(access2=11.7, obesity=50.5, csmoking=25, diabetes=15, bphigh=42),
        "Fenton": _row(access2=5.3, obesity=34.8, csmoking=15, diabetes=9, bphigh=30),
    }
    rankings = fh.build_city_rankings(city_rows)

    # one ranked list per COMPARE measure
    assert set(rankings) == set(fh.COMPARE)

    uninsured = rankings["access2"]
    assert [c["value"] for c in uninsured] == [11.7, 8.1, 5.3]   # high-to-low
    assert [c["name"] for c in uninsured] == ["Flint", "Burton", "Fenton"]
    assert any(c["name"] == "Burton" for c in uninsured)         # Burton included


def test_city_rankings_skips_missing_measure():
    city_rows = {
        "Burton": _row(access2=8.1),
        "Clio": _row(obesity=39.1),   # no access2 value
    }
    rankings = fh.build_city_rankings(city_rows)
    assert [c["name"] for c in rankings["access2"]] == ["Burton"]   # Clio dropped
    assert [c["name"] for c in rankings["obesity"]] == ["Clio"]


def test_uninsured_trend_is_two_lines(monkeypatch, tmp_path):
    """Burton vs Michigan multi-line uninsured trend (no network)."""
    monkeypatch.setattr(fh, "ACS_TREND_CACHE", str(tmp_path / "cache.json"))
    monkeypatch.setattr(fh, "ACS_TREND_YEARS", [2013, 2018, 2023])
    vals = {
        "Burton": {2013: 15.0, 2018: 9.1, 2023: 10.0},
        "Michigan": {2013: 12.0, 2018: 7.0, 2023: 8.0},
    }

    def fake(year, key, geo):
        return vals["Burton" if "place" in geo else "Michigan"][year]

    monkeypatch.setattr(fh, "_acs_uninsured_pct", fake)

    chart = fh.build_uninsured_trend("fakekey")
    assert chart is not None
    assert chart["type"] == "trend"
    assert "lines" in chart and "points" not in chart
    assert [ln["label"] for ln in chart["lines"]] == ["Burton", "Michigan"]
    assert chart["lines"][0]["points"][0] == {"x": "2013", "y": 15.0}
    assert "Burton vs Michigan" in chart["title"]
