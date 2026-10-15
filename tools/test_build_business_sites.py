"""Tests for build_business_sites.py: CSV validation, class split, clipping, popup and
panel shaping. No network: rows get coordinates set directly.
Run: python -m pytest tools/test_build_business_sites.py -q
"""
import csv
import json
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_business_sites as bbs  # noqa: E402

TODAY = date(2026, 10, 15)
COLS = ["parcel", "street", "city", "zip", "propclass", "acres", "frontage", "zoning"]
SQUARE = [[[-84.0, 42.5], [-83.0, 42.5], [-83.0, 43.5], [-84.0, 43.5], [-84.0, 42.5]]]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def _raw(**kw):
    base = {"parcel": "59-1", "street": "1000 S CENTER RD", "city": "BURTON", "zip": "48519",
            "propclass": "202", "acres": "1.25", "frontage": "120", "zoning": "C-2"}
    base.update(kw)
    return base


def _rows(tmp_path, raws):
    p = tmp_path / "c.csv"
    _write(p, raws)
    return bbs.read_rows(str(p))


def test_read_rows_keeps_only_the_four_classes_and_parses(tmp_path):
    rows = _rows(tmp_path, [_raw(), _raw(parcel="2", propclass="251"), _raw(parcel="3", propclass="301", acres="")])
    assert [r["propclass"] for r in rows] == ["202", "301"]
    assert rows[0]["acres"] == 1.25 and rows[0]["frontage"] == 120
    assert rows[1]["acres"] == 0


def test_read_rows_fails_loud(tmp_path):
    with pytest.raises(SystemExit, match="twice"):
        _rows(tmp_path, [_raw(), _raw()])
    with pytest.raises(SystemExit, match="bad number"):
        _rows(tmp_path, [_raw(acres="one")])
    p = tmp_path / "x.csv"
    p.write_text("parcel,street\n1,a\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing columns"):
        bbs.read_rows(str(p))


def test_read_summary_validates(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"transfers24": 37, "asOf": "2026-10-15"}), encoding="utf-8")
    assert bbs.read_summary(str(p))["transfers24"] == 37
    p.write_text(json.dumps({"transfers24": "37"}), encoding="utf-8")
    with pytest.raises(SystemExit):
        bbs.read_summary(str(p))


def test_layers_split_by_vacancy_and_clip(tmp_path):
    rows = _rows(tmp_path, [
        _raw(parcel="v1", propclass="202", acres="6"),
        _raw(parcel="v2", propclass="302", acres="0.5", street="20 B RD"),
        _raw(parcel="b1", propclass="201", street="30 C RD"),
        _raw(parcel="out", propclass="201", street="40 D RD"),
        _raw(parcel="none", propclass="301", street="50 E RD"),
    ])
    for r in rows[:3]:
        r.update(lat=43.0, lng=-83.6)
    rows[3].update(lat=10.0, lng=10.0)
    vacant, improved, nocoord, outside = bbs.build_layers(rows, SQUARE)
    assert [f["properties"]["parcel"] for f in vacant["features"]] == ["v1", "v2"]  # largest first
    assert [f["properties"]["parcel"] for f in improved["features"]] == ["b1"]
    assert (nocoord, outside) == (1, 1)
    big = vacant["features"][0]["properties"]
    assert big["_radius"] > vacant["features"][1]["properties"]["_radius"]
    assert big["_color"] == bbs.CLASSES["202"]["color"]
    assert ["Lot size", "6 acres"] in big["_popupRows"]
    assert all(len(r) == 2 for f in vacant["features"] for r in f["properties"]["_popupRows"])
    # the public feature carries nothing beyond the approved fields
    assert set(big) <= {"name", "parcel", "propclass", "acres", "zoning", "_color", "_radius", "_popupRows"}


def test_panel_counts_charts_and_top_table(tmp_path):
    rows = _rows(tmp_path, [
        _raw(parcel="1", propclass="202", acres="2", zoning="C-2"),
        _raw(parcel="2", propclass="202", acres="3", zoning="C-2", street="2 X"),
        _raw(parcel="3", propclass="302", acres="10", zoning="M-1", street="3 X"),
        _raw(parcel="4", propclass="201", acres="1", street="4 X"),
        _raw(parcel="5", propclass="301", acres="4", street="5 X"),
    ])
    panel = bbs.build_panel(rows, {"transfers24": 37, "asOf": "2026-10-15"}, 2, 1, TODAY)
    s = {x["label"]: x["value"] for x in panel["stats"]}
    assert s["Vacant commercial parcels"] == "2" and s["Vacant industrial parcels"] == "1"
    assert s["Commercial buildings"] == "1" and s["Industrial buildings"] == "1"
    assert s["Commercial and industrial buildings sold, last 24 months"] == "37"
    acres = {x["label"]: x["value"] for x in panel["charts"][0]["series"]}
    assert acres["Vacant industrial land"] == 10 and acres["Vacant commercial land"] == 5
    zoning = {x["label"]: x["value"] for x in panel["charts"][1]["series"]}
    assert zoning == {"C-2": 2, "M-1": 1}
    table = panel["tables"][0]
    assert table["rows"][0]["cells"][0] == "3 X" and table["rows"][0]["cells"][2] == "10"
    assert all(len(r["cells"]) == len(table["columns"]) for r in table["rows"])
    assert any("3 parcels could not be placed" in n for n in panel["notes"])
    assert "2026-10-15" in panel["source"]


def test_centroids_override_and_validate(tmp_path):
    rows = _rows(tmp_path, [_raw(parcel="a"), _raw(parcel="b", street="2 X")])
    p = tmp_path / "cent.csv"
    p.write_text("parcel,lat,lng" + chr(10) + "a,43.01,-83.61" + chr(10) + "zzz,1,1" + chr(10), encoding="utf-8")
    assert bbs.apply_centroids(rows, bbs.read_centroids(str(p))) == 1
    assert (rows[0]["lat"], rows[0]["lng"]) == (43.01, -83.61) and rows[1]["lat"] is None
    assert bbs.read_centroids(str(tmp_path / "missing.csv")) == {}
    p.write_text("parcel,lat" + chr(10) + "a,1" + chr(10), encoding="utf-8")
    with pytest.raises(SystemExit, match="missing column"):
        bbs.read_centroids(str(p))
