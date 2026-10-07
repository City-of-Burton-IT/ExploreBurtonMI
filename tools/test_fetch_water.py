"""Unit tests for the Drinking Water builder's lead (PB90) handling (no network).

Issue #140: on 2026-10-06 a transient Envirofacts failure was swallowed and the
regenerated panel silently dropped the "Lead (90th percentile)" stat. The tool
must now stop, non-zero, before writing when the lead result is unavailable.
Run: python -m pytest tools/test_fetch_water.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fetch_water as fw  # noqa: E402

PWSID = fw.PWSID
SAMPLES_URL = f"{fw.EF}/LCR_SAMPLE/PWSID/{PWSID}/JSON"
RESULTS_URL = f"{fw.EF}/LCR_SAMPLE_RESULT/PWSID/{PWSID}/JSON"
SYSTEM_URL = f"{fw.EF}/WATER_SYSTEM/PWSID/{PWSID}/JSON"
VIOLATION_URL = f"{fw.EF}/VIOLATION/PWSID/{PWSID}/JSON"


def _samples():
    return [
        {"sample_id": "A", "sampling_end_date": "2022-12-31 00:00:00"},
        {"sample_id": "B", "sampling_end_date": "2023-12-31 00:00:00"},
    ]


def _results(code="PB90"):
    return [
        {"sample_id": "A", "contaminant_code": code, "sample_measure": 0, "unit_of_measure": "mg/L"},
        {"sample_id": "B", "contaminant_code": code, "sample_measure": 0.002, "unit_of_measure": "mg/L"},
    ]


def _fake_get(table: dict):
    """A _get stand-in keyed by URL; a value that is an Exception is raised."""
    def get(url):
        v = table[url]
        if isinstance(v, Exception):
            raise v
        return v
    return get


# --- fetch_lead -------------------------------------------------------------------

def test_fetch_lead_returns_latest_period_and_peak(monkeypatch):
    monkeypatch.setattr(fw, "_get", _fake_get({SAMPLES_URL: _samples(), RESULTS_URL: _results()}))
    lead = fw.fetch_lead()
    assert lead == {"value": 0.002, "unit": "mg/L", "last_year": "2023",
                    "first_year": "2022", "periods": 2, "peak": 0.002}


def test_fetch_lead_raises_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(fw, "_get", _fake_get({
        SAMPLES_URL: RuntimeError("all 4 attempts failed"), RESULTS_URL: _results()}))
    with pytest.raises(fw.LeadUnavailable, match="fetch failed"):
        fw.fetch_lead()


def test_fetch_lead_raises_when_no_pb90_rows(monkeypatch):
    monkeypatch.setattr(fw, "_get", _fake_get({SAMPLES_URL: _samples(), RESULTS_URL: _results("CU90")}))
    with pytest.raises(fw.LeadUnavailable, match="none with contaminant_code PB90"):
        fw.fetch_lead()


# --- main: lead unavailable must not rewrite the committed panel -------------------

def _system_tables(lead_results):
    return {
        SYSTEM_URL: [{"population_served_count": "28000", "service_connections_count": "11000",
                      "primary_source_code": "SWP"}],
        VIOLATION_URL: [],
        SAMPLES_URL: _samples(),
        RESULTS_URL: lead_results,
    }


def test_main_exits_nonzero_and_does_not_write_when_lead_missing(monkeypatch, tmp_path):
    out = tmp_path / "info-water.json"
    monkeypatch.setattr(fw, "OUT", str(out))
    monkeypatch.setattr(fw, "_get", _fake_get(_system_tables([])))
    with pytest.raises(SystemExit) as exc:
        fw.main([])
    assert exc.value.code != 0
    assert "Not writing" in str(exc.value.code)
    assert not out.exists()


def test_main_allow_missing_lead_builds_without_the_stat(monkeypatch, tmp_path, capsys):
    out = tmp_path / "info-water.json"
    written = {}
    monkeypatch.setattr(fw, "OUT", str(out))
    monkeypatch.setattr(fw, "write_json", lambda path, obj: written.update(path=path, obj=obj))
    monkeypatch.setattr(fw, "_get", _fake_get(_system_tables([])))
    fw.main(["--allow-missing-lead"])
    labels = [s["label"] for s in written["obj"]["stats"]]
    assert "Lead (90th percentile)" not in labels
    assert "building without the lead stat" in capsys.readouterr().err


def test_main_writes_lead_stat_when_available(monkeypatch, tmp_path):
    out = tmp_path / "info-water.json"
    written = {}
    monkeypatch.setattr(fw, "OUT", str(out))
    monkeypatch.setattr(fw, "write_json", lambda path, obj: written.update(path=path, obj=obj))
    monkeypatch.setattr(fw, "_get", _fake_get(_system_tables(_results())))
    fw.main([])
    stats = {s["label"]: s for s in written["obj"]["stats"]}
    assert stats["Lead (90th percentile)"]["value"] == "0.002 mg/L"
    assert "tested 2023" in stats["Lead (90th percentile)"]["hint"]
    assert written["obj"]["notes"][0].startswith("Under the federal Lead & Copper Rule")
