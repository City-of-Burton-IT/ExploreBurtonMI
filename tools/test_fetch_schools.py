# Tests for fetch_schools.py.
#
# PRIORITY: the _get retry/backoff helper (the Urban Institute API is flaky
# under load) is exercised with a stubbed urllib.request.urlopen and a stubbed
# time.sleep so the tests are instant and touch no network. Also covers the
# pure parsing helpers (load_districts, district_stats' directory/fallback
# branching) with synthetic fixtures.
# Run: python -m pytest tools/test_fetch_schools.py -q
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fetch_schools as fs  # noqa: E402


class FakeResp:
    """Minimal stand-in for the context-manager object urllib.request.urlopen
    returns; json.load(resp) just needs a .read()-able file-like object."""

    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return io.BytesIO(json.dumps(self._payload).encode("utf-8"))

    def __exit__(self, exc_type, exc, tb):
        return False


# --- _get: retry/backoff -----------------------------------------------------------

def test_get_succeeds_on_first_try(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(timeout)
        return FakeResp({"ok": True})

    sleeps = []
    monkeypatch.setattr(fs.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(fs.time, "sleep", lambda s: sleeps.append(s))

    out = fs._get("http://example.test/x")

    assert out == {"ok": True}
    assert len(calls) == 1
    assert sleeps == []


def test_get_retries_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    def fake_urlopen(req, timeout=None):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("simulated transient failure")
        return FakeResp({"ok": True})

    sleeps = []
    monkeypatch.setattr(fs.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(fs.time, "sleep", lambda s: sleeps.append(s))

    out = fs._get("http://example.test/x", attempts=5)

    assert out == {"ok": True}
    assert attempts["n"] == 3
    assert sleeps == [2, 4]  # backoff formula: 2 + i*2, for the two failed tries


def test_get_exhausts_attempts_and_raises(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("always fails")

    sleeps = []
    monkeypatch.setattr(fs.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(fs.time, "sleep", lambda s: sleeps.append(s))

    with pytest.raises(RuntimeError, match="all 3 attempts failed"):
        fs._get("http://example.test/x", attempts=3)

    assert len(sleeps) == 2  # no sleep after the final (3rd) failure


def test_get_does_not_sleep_after_the_last_attempt(monkeypatch):
    # Guards the `if i < attempts - 1` branch specifically: exactly attempts-1 sleeps.
    monkeypatch.setattr(fs.urllib.request, "urlopen",
                         lambda req, timeout=None: (_ for _ in ()).throw(OSError("boom")))
    sleeps = []
    monkeypatch.setattr(fs.time, "sleep", lambda s: sleeps.append(s))
    with pytest.raises(RuntimeError):
        fs._get("http://example.test/x", attempts=1)
    assert sleeps == []  # a single attempt never sleeps


# --- load_districts -----------------------------------------------------------------

def _write_districts_geojson(tmp_path, features):
    path = tmp_path / "school-districts.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return str(path)


def test_load_districts_reads_leaid_and_name(tmp_path, monkeypatch):
    features = [
        {"properties": {"geoid": "2603540", "name": "Atherton Community Schools"}},
        {"properties": {"geoid": "2604740", "name": "Bendle Public Schools"}},
    ]
    monkeypatch.setattr(fs, "DISTRICTS_GEOJSON", _write_districts_geojson(tmp_path, features))

    out = fs.load_districts()

    assert out == [
        {"leaid": "2603540", "name": "Atherton Community Schools"},
        {"leaid": "2604740", "name": "Bendle Public Schools"},
    ]


def test_load_districts_skips_features_missing_geoid_or_name(tmp_path, monkeypatch):
    features = [
        {"properties": {"geoid": "", "name": "No GEOID District"}},
        {"properties": {"geoid": "2603540", "name": ""}},
        {"properties": {"geoid": "2604740", "name": "Bendle Public Schools"}},
    ]
    monkeypatch.setattr(fs, "DISTRICTS_GEOJSON", _write_districts_geojson(tmp_path, features))

    out = fs.load_districts()

    assert out == [{"leaid": "2604740", "name": "Bendle Public Schools"}]


def test_load_districts_raises_when_none_found(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, "DISTRICTS_GEOJSON", _write_districts_geojson(tmp_path, []))
    with pytest.raises(SystemExit, match="No districts found"):
        fs.load_districts()


# --- district_stats: directory + grade-99 fallback -----------------------------------

def test_district_stats_reads_directory_enrollment_and_teachers(monkeypatch):
    def fake_get(url):
        assert "directory/2023" in url
        return {"results": [{"enrollment": 4200, "teachers_total_fte": 210.5}]}

    monkeypatch.setattr(fs, "_get", fake_get)
    enr, teachers = fs.district_stats("2603540", 2023)
    assert enr == 4200
    assert teachers == 210.5


def test_district_stats_falls_back_to_grade99_when_directory_enrollment_null(monkeypatch):
    def fake_get(url):
        if "directory" in url:
            return {"results": [{"enrollment": None, "teachers_total_fte": 100.0}]}
        assert "enrollment/2023/grade-99" in url
        return {"results": [
            {"race": 1, "sex": 1, "enrollment": 999},  # not the race=99/sex=99 total row
            {"race": 99, "sex": 99, "enrollment": 3800},
        ]}

    monkeypatch.setattr(fs, "_get", fake_get)
    enr, teachers = fs.district_stats("2603540", 2023)
    assert enr == 3800
    assert teachers == 100.0


def test_district_stats_falls_back_when_directory_call_raises(monkeypatch):
    def fake_get(url):
        if "directory" in url:
            raise RuntimeError("522 from upstream")
        return {"results": [{"race": 99, "sex": 99, "enrollment": 1234}]}

    monkeypatch.setattr(fs, "_get", fake_get)
    enr, teachers = fs.district_stats("2603540", 2023)
    assert enr == 1234
    assert teachers is None  # directory (the only teacher source) failed


def test_district_stats_returns_none_none_when_everything_fails(monkeypatch):
    def fake_get(url):
        raise RuntimeError("down")

    monkeypatch.setattr(fs, "_get", fake_get)
    enr, teachers = fs.district_stats("2603540", 2023)
    assert enr is None
    assert teachers is None


def test_district_stats_ignores_zero_or_empty_teacher_fte(monkeypatch):
    def fake_get(url):
        return {"results": [{"enrollment": 500, "teachers_total_fte": 0}]}

    monkeypatch.setattr(fs, "_get", fake_get)
    enr, teachers = fs.district_stats("2603540", 2023)
    assert enr == 500
    assert teachers is None  # 0 is treated as "not present"


# --- build_panel: light coverage of the aggregation shape ----------------------------

def test_build_panel_sorts_series_and_flags_missing(monkeypatch):
    def fake_stats(leaid, year):
        return {"2603540": (500, 25.0), "2604740": (None, None)}[leaid]

    monkeypatch.setattr(fs, "district_stats", fake_stats)
    districts = [
        {"leaid": "2603540", "name": "Atherton Community Schools"},
        {"leaid": "2604740", "name": "Bendle Public Schools"},
    ]
    panel = fs.build_panel(districts, 2023)

    series = panel["charts"][0]["series"]
    assert series == [{"label": "Atherton", "value": 500}]
    assert any("Bendle" in n for n in panel["notes"])  # missing-enrollment note
    assert panel["stats"][0] == {"label": "Districts serving Burton", "value": "2",
                                  "hint": "public school districts"}
