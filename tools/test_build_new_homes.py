"""Tests for build_new_homes.py. No network; rows get coordinates set directly.
Run: python -m pytest tools/test_build_new_homes.py -q
"""
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_new_homes as bnh  # noqa: E402

SQUARE = [[[-84.0, 42.5], [-83.0, 42.5], [-83.0, 43.5], [-84.0, 43.5], [-84.0, 42.5]]]
COLS = ["parcel", "street", "city", "zip", "year", "units"]


def _rows(tmp_path, raws):
    p = tmp_path / "n.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in raws:
            w.writerow({c: r.get(c, "") for c in COLS})
    return bnh.read_rows(str(p))


def test_read_rows_skips_blank_street_and_floors_units(tmp_path):
    rows = _rows(tmp_path, [{"street": "1 A ST", "year": "2024", "units": "0"},
                            {"street": "", "year": "2024", "units": "1"}])
    assert len(rows) == 1 and rows[0]["units"] == 1 and rows[0]["year"] == 2024


def test_read_rows_fails_loud(tmp_path):
    with pytest.raises(SystemExit, match="bad number"):
        _rows(tmp_path, [{"street": "1 A ST", "year": "twenty", "units": "1"}])
    p = tmp_path / "x.csv"
    p.write_text("street,year" + chr(10) + "a,2024" + chr(10), encoding="utf-8")
    with pytest.raises(SystemExit, match="missing columns"):
        bnh.read_rows(str(p))


def test_band_color_by_age():
    assert bnh.band_color(2026, 2026) == bnh.BAND_COLORS[0]
    assert bnh.band_color(2024, 2026) == bnh.BAND_COLORS[1]
    assert bnh.band_color(2021, 2026) == bnh.BAND_COLORS[2]
    assert bnh.band_color(2015, 2026) == bnh.BAND_COLORS[3]


def test_build_merges_same_address_year_and_clips(tmp_path):
    rows = _rows(tmp_path, [
        {"street": "1 A ST", "year": "2024", "units": "1"},
        {"street": "1 a st", "year": "2024", "units": "1"},   # same address-year: merged
        {"street": "1 A ST", "year": "2022", "units": "1"},   # different year: own pin
        {"street": "9 OUT RD", "year": "2024", "units": "1"},
        {"street": "9 NONE RD", "year": "2024", "units": "1"},
    ])
    for r in rows[:3]:
        r.update(lat=43.0, lng=-83.6)
    rows[3].update(lat=10.0, lng=10.0)
    fc, nocoord, outside = bnh.build(rows, SQUARE, 2026)
    assert (nocoord, outside) == (1, 1)
    assert [f["properties"]["year"] for f in fc["features"]] == [2024, 2022]  # newest first
    merged = fc["features"][0]["properties"]
    assert merged["units"] == 2 and ["Homes permitted here", "2 (2 permits)"] in merged["_popupRows"]
    assert set(merged) <= {"name", "year", "units", "_color", "_radius", "_popupRows"}


def test_geocode_prefers_parcel_centroid(tmp_path):
    rows = _rows(tmp_path, [{"parcel": "p1", "street": "1 A ST", "year": "2024", "units": "1"},
                            {"parcel": "p2", "street": "", "year": "2024", "units": "1"}])
    hit = bnh.geocode(rows, {"p1": (43.0, -83.6), "p2": (43.1, -83.7)})
    assert hit == 2 and rows[1]["lat"] == 43.1
    assert bnh.read_centroids("C:/nonexistent.csv") == {}
