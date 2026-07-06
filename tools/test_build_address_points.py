# Tests for build_address_points.py.
#
# PRIORITY: geocode_batch's parsing of the Census batch-geocoder's header-less
# CSV response (~lines 171-186) -- correct Match rows, No_Match rows, and
# malformed/reordered rows (a Match status with the coordinate column missing).
# These tests document current behavior rather than changing it: a "Match" row
# that is missing the coordinate field is silently treated as a cache miss (no
# exception, no coordinates set) because the code only special-cases the
# `len(parsed) >= 6 and parsed[5]` branch and falls through to `else` otherwise.
#
# requests.post is stubbed (monkeypatch) so no network call is ever made, and
# CACHE is redirected into tmp_path so the real geocode cache file is untouched.
# Run: python -m pytest tools/test_build_address_points.py -q
import csv
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_address_points as bap  # noqa: E402


def _csv_text(rows: list[list]) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def _match_row(rid, street, city, state, zip_, lat, lon):
    matched = f"{street.upper()}, {city.upper()}, {state}, {zip_}"
    return [rid, f"{street}, {city}, {state}, {zip_}", "Match", "Exact", matched,
            f"{lon},{lat}", "12345", "L"]


def _no_match_row(rid, street, city, state, zip_):
    return [rid, f"{street}, {city}, {state}, {zip_}", "No_Match"]


def _fake_post(response_text):
    class FakeResp:
        text = response_text

        def raise_for_status(self):
            pass

    def fake(url, files=None, data=None, timeout=None):
        return FakeResp()

    return fake


def _row(street="100 Main St", city="Burton", state="MI", zip_="48509", rid="0"):
    return {"id": rid, "street": street, "city": city, "state": state, "zip": zip_,
            "lat": None, "lng": None}


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(bap, "CACHE", str(tmp_path / "address_geocode.json"))
    monkeypatch.setattr(bap.time, "sleep", lambda s: None)


# --- geocode_batch: response CSV parsing --------------------------------------------

def test_geocode_batch_parses_a_matched_row(monkeypatch):
    rows = [_row()]
    text = _csv_text([_match_row("0", "100 Main St", "Burton", "MI", "48509", 42.996, -83.611)])
    monkeypatch.setattr(bap.requests, "post", _fake_post(text))

    cache = {}
    bap.geocode_batch(rows, cache)

    assert rows[0]["lat"] == pytest.approx(42.996)
    assert rows[0]["lng"] == pytest.approx(-83.611)
    key = bap._addr_key("100 Main St", "Burton", "MI", "48509")
    assert cache[key] == [pytest.approx(42.996), pytest.approx(-83.611)]


def test_geocode_batch_records_no_match_as_a_cache_miss(monkeypatch):
    rows = [_row(street="999 Nowhere Rd")]
    text = _csv_text([_no_match_row("0", "999 Nowhere Rd", "Burton", "MI", "48509")])
    monkeypatch.setattr(bap.requests, "post", _fake_post(text))

    cache = {}
    bap.geocode_batch(rows, cache)

    assert rows[0]["lat"] is None and rows[0]["lng"] is None
    key = bap._addr_key("999 Nowhere Rd", "Burton", "MI", "48509")
    assert cache[key] is None


def test_geocode_batch_documents_malformed_match_row_is_silently_treated_as_miss(monkeypatch):
    # A "Match" row with the lon/lat column missing (reordered/truncated columns):
    # the code's guard is `match == "Match" and len(parsed) >= 6 and parsed[5]`,
    # so this 5-column row falls into the `else` branch just like a No_Match --
    # no exception is raised and the row's coordinates are left unset.
    rows = [_row()]
    malformed = ["0", "100 Main St, Burton, MI, 48509", "Match", "Exact",
                 "100 MAIN ST, BURTON, MI, 48509"]  # missing lon/lat column
    text = _csv_text([malformed])
    monkeypatch.setattr(bap.requests, "post", _fake_post(text))

    cache = {}
    bap.geocode_batch(rows, cache)

    assert rows[0]["lat"] is None and rows[0]["lng"] is None  # current behavior: silent miss
    key = bap._addr_key("100 Main St", "Burton", "MI", "48509")
    assert cache[key] is None


def test_geocode_batch_skips_rows_with_fewer_than_three_columns(monkeypatch):
    # len(parsed) < 3 rows are `continue`d entirely -- no cache write at all,
    # not even a miss. A stray blank line is enough to trigger this.
    rows = [_row()]
    text = _csv_text([_match_row("0", "100 Main St", "Burton", "MI", "48509", 42.0, -83.0)]) + "\n"
    monkeypatch.setattr(bap.requests, "post", _fake_post(text))

    cache = {}
    bap.geocode_batch(rows, cache)
    # the real match row still parses fine; the trailing blank line is ignored
    assert rows[0]["lat"] == pytest.approx(42.0)


def test_geocode_batch_ignores_response_rows_whose_id_is_not_in_the_chunk(monkeypatch):
    rows = [_row(rid="0")]
    text = _csv_text([_match_row("999", "100 Main St", "Burton", "MI", "48509", 42.0, -83.0)])
    monkeypatch.setattr(bap.requests, "post", _fake_post(text))

    cache = {}
    bap.geocode_batch(rows, cache)

    assert rows[0]["lat"] is None  # id "999" doesn't match row "0"; nothing recorded
    assert cache == {}


def test_geocode_batch_skips_rows_that_already_have_coordinates(monkeypatch):
    def fail_post(*a, **k):
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr(bap.requests, "post", fail_post)
    rows = [{"id": "0", "street": "1 Main St", "city": "Burton", "state": "MI",
             "zip": "48509", "lat": 42.5, "lng": -83.5}]
    bap.geocode_batch(rows, {})
    assert rows[0]["lat"] == 42.5  # unchanged, never sent to the geocoder


def test_geocode_batch_uses_the_cache_before_calling_the_geocoder(monkeypatch):
    def fail_post(*a, **k):
        raise AssertionError("requests.post should not be called for a cached address")

    monkeypatch.setattr(bap.requests, "post", fail_post)
    rows = [_row()]
    key = bap._addr_key("100 Main St", "Burton", "MI", "48509")
    cache = {key: [42.111, -83.222]}
    bap.geocode_batch(rows, cache)
    assert rows[0]["lat"] == 42.111
    assert rows[0]["lng"] == -83.222


def test_geocode_batch_caches_a_prior_miss_as_none_and_leaves_coords_unset(monkeypatch):
    def fail_post(*a, **k):
        raise AssertionError("requests.post should not be called for a cached miss")

    monkeypatch.setattr(bap.requests, "post", fail_post)
    rows = [_row()]
    key = bap._addr_key("100 Main St", "Burton", "MI", "48509")
    cache = {key: None}
    bap.geocode_batch(rows, cache)
    assert rows[0]["lat"] is None and rows[0]["lng"] is None


# --- other pure helpers ---------------------------------------------------------------

def test_titlecase_street_keeps_single_letter_directionals_uppercase():
    assert bap.titlecase_street("1001 S CENTER RD") == "1001 S Center Rd"


def test_titlecase_street_handles_mixed_tokens():
    assert bap.titlecase_street("500 W CORUNNA AVE") == "500 W Corunna Ave"


def test_addr_key_joins_nonempty_parts():
    assert bap._addr_key("100 Main St", "Burton", "MI", "48509") == "100 Main St, Burton, MI, 48509"
    assert bap._addr_key("100 Main St", "", "MI", "") == "100 Main St, MI"


def test_norm_collapses_whitespace():
    assert bap._norm("  100   Main   St  ") == "100 Main St"
    assert bap._norm(None) == ""


# --- read_source_rows: dedupe + defaults -----------------------------------------------

def test_read_source_rows_defaults_and_dedupes(tmp_path, monkeypatch):
    csv_text = (
        "street,city,state,zip\n"
        "100 Main St,,,\n"          # blank city/state -> DEFAULT_CITY/DEFAULT_STATE
        "100 Main St,Burton,MI,\n"  # same normalized key (case-insensitive) -> dropped
        "200 Oak Ave,Flint,MI,48504\n"
        ",Burton,MI,48509\n"        # blank street -> skipped entirely
    )
    src = tmp_path / "source.csv"
    src.write_text(csv_text, encoding="utf-8")
    monkeypatch.setattr(bap, "SOURCE_CSV", str(src))

    rows = bap.read_source_rows()

    assert len(rows) == 2
    assert rows[0]["street"] == "100 Main St"
    assert rows[0]["city"] == "Burton"  # DEFAULT_CITY applied
    assert rows[0]["state"] == "MI"     # DEFAULT_STATE applied
    assert rows[1]["street"] == "200 Oak Ave"


def test_read_source_rows_missing_file_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(bap, "SOURCE_CSV", str(tmp_path / "does-not-exist.csv"))
    with pytest.raises(SystemExit, match="Source export not found"):
        bap.read_source_rows()


# --- in_city / ray casting ---------------------------------------------------------------

SQUARE = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]  # a 10x10 lng/lat box


def test_in_city_true_for_a_point_inside_the_ring():
    assert bap.in_city(5, 5, [SQUARE]) is True


def test_in_city_false_for_a_point_outside_the_ring():
    assert bap.in_city(20, 20, [SQUARE]) is False
