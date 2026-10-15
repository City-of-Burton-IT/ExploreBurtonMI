"""Tests for build_sales_tiles.py: qualifying rules, multi-parcel collapse, block-group
assignment, the five-sale suppression and panel shaping. No network, no repo files:
rows are built in memory and block groups are two synthetic squares.
Run: python -m pytest tools/test_build_sales_tiles.py -q
"""
import csv
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_sales_tiles as bst  # noqa: E402

TODAY = date(2026, 10, 15)
COLS = ["parcel", "street", "city", "zip", "saledate", "price", "propclass", "terms",
        "instr", "sqft", "vacant", "liberpage"]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def _raw(**kw):
    base = {"parcel": "59-1", "street": "100 MAIN ST", "city": "BURTON", "zip": "48519",
            "saledate": "2026-06-01", "price": "150000", "propclass": "401",
            "terms": "03-ARM'S LENGTH", "instr": "WD", "sqft": "1200", "vacant": "0", "liberpage": ""}
    base.update(kw)
    return base


def test_read_rows_applies_qualifying_rules(tmp_path):
    p = tmp_path / "s.csv"
    _write(p, [
        _raw(parcel="keep"),
        _raw(parcel="zero", price="0"),
        _raw(parcel="vacant", vacant="1"),
        _raw(parcel="commercial", propclass="201"),
    ])
    rows = bst.read_rows(str(p))
    assert [r["street"] for r in rows] == ["100 Main St".upper()]
    assert rows[0]["date"] == date(2026, 6, 1) and rows[0]["price"] == 150000


def test_read_rows_fails_loud(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("parcel,street\n1,x\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing columns"):
        bst.read_rows(str(p))
    q = tmp_path / "t.csv"
    _write(q, [_raw(saledate="06/01/2026")])
    with pytest.raises(SystemExit, match="bad number or date"):
        bst.read_rows(str(q))


def test_collapse_multi_parcel_counts_once_and_drops_sqft(tmp_path):
    p = tmp_path / "s.csv"
    _write(p, [
        _raw(parcel="a", liberpage="L1/P1", price="300000", sqft="1500"),
        _raw(parcel="b", liberpage="L1/P1", price="300000", sqft="900", street="102 MAIN ST"),
        _raw(parcel="c", liberpage="L2/P2", price="120000", sqft="1000"),
        _raw(parcel="d", liberpage="", price="99000"),
        _raw(parcel="e", liberpage="", price="99000"),  # no liber: never collapsed
    ])
    rows = bst.collapse_multi_parcel(bst.read_rows(str(p)))
    prices = [r["price"] for r in rows]
    assert prices == [300000, 120000, 99000, 99000]
    assert rows[0]["sqft"] == 0          # combined price: no $/sqft
    assert rows[1]["sqft"] == 1000       # single-parcel sale keeps its floor area


def _groups():
    def square(geoid, name, x0, y0):
        ring = [[x0, y0], [x0 + 1, y0], [x0 + 1, y0 + 1], [x0, y0 + 1], [x0, y0]]
        return {"geoid": geoid, "name": name, "geometry": {"type": "Polygon", "coordinates": [ring]},
                "rings": [ring]}
    return [square("A", "Group A", 0, 0), square("B", "Group B", 10, 10)]


def _sale(lng, lat, price, days_ago, sqft=1000):
    return {"street": "x", "city": "Burton", "zip": "", "date": TODAY - timedelta(days=days_ago),
            "price": price, "sqft": sqft, "liberpage": "", "lat": lat, "lng": lng}


def test_assign_places_points_and_counts_unplaced():
    rows = [_sale(0.5, 0.5, 100, 1), _sale(10.5, 10.5, 200, 1), _sale(50, 50, 300, 1),
            dict(_sale(0.5, 0.5, 400, 1), lat=None, lng=None)]
    by_group, unassigned = bst.assign(rows, _groups())
    assert {k: len(v) for k, v in by_group.items()} == {"A": 1, "B": 1}
    assert unassigned == 2


def test_group_stats_suppresses_below_five_and_computes_change():
    cur = [_sale(0.5, 0.5, p, 30 + i) for i, p in enumerate([100, 110, 120, 130, 140, 150])]
    prior = [_sale(0.5, 0.5, p, 800 + i) for i, p in enumerate([80, 90, 100, 110, 120])]
    few = [_sale(10.5, 10.5, 500, 10) for _ in range(4)]
    by_group, _ = bst.assign(cur + prior + few, _groups())
    stats = bst.group_stats(by_group, _groups(), TODAY)
    a, b = stats
    assert a["cur"] == {"n": 6, "median": 125, "ppsf": 0}  # median(100..150)=125; 125/1000 rounds to 0
    assert a["prior"]["median"] == 100 and a["change"] == 25
    assert b["cur"] == {"n": 4, "median": None, "ppsf": None} and b["change"] is None


def test_geojson_styles_shown_and_suppressed_groups():
    cur = [_sale(0.5, 0.5, 100000 + i, 30 + i, sqft=1000) for i in range(5)]
    few = [_sale(10.5, 10.5, 500, 10)]
    by_group, _ = bst.assign(cur + few, _groups())
    stats = bst.group_stats(by_group, _groups(), TODAY)
    fc = bst.build_geojson(stats, TODAY)
    a, b = fc["features"]
    assert a["properties"]["_color"] != bst.SUPPRESSED and a["properties"]["_fillOpacity"] > 0.5
    assert a["properties"]["median"] == 100002
    assert b["properties"]["_color"] == bst.SUPPRESSED and b["properties"]["median"] is None
    assert ["Arms-length home sales", "1 to 4 (Oct 2024 to Oct 2026)"] == b["properties"]["_popupRows"][0]
    assert all(len(r) == 2 for f in fc["features"] for r in f["properties"]["_popupRows"])
    # nothing parcel-level leaks into the public file
    assert not any(k in a["properties"] for k in ("street", "parcel", "date", "price"))


def test_panel_shapes_and_count_labels():
    cur = [_sale(0.5, 0.5, 100000 + i * 10000, 30 + i, sqft=1000) for i in range(6)]
    by_group, _ = bst.assign(cur, _groups())
    stats = bst.group_stats(by_group, _groups(), TODAY)
    panel = bst.build_panel(cur, stats, 3, TODAY)
    labels = {s["label"]: s["value"] for s in panel["stats"]}
    assert labels["Arms-length home sales, last 24 months"] == "6"
    assert labels["Citywide median sale price"] == "$125,000"
    assert labels["Neighbourhoods with a shown price"] == "1 of 2"
    assert panel["charts"][0]["type"] == "trend" and panel["charts"][1]["type"] == "bars"
    assert sum(s["value"] for s in panel["charts"][1]["series"]) == 6
    table = panel["tables"][0]
    assert all(len(r["cells"]) == len(table["columns"]) for r in table["rows"])
    assert table["rows"][0]["cells"][0] == "Group A"      # shown groups sort first
    assert table["rows"][1]["cells"][2:4] == ["0", "n/a"]  # empty group: count 0, no price
    assert any("3 qualifying sales could not be placed" in n for n in panel["notes"])


def test_count_label_buckets_small_counts():
    assert bst._count_label(0) == "0"
    assert bst._count_label(3) == "1 to 4"
    assert bst._count_label(5) == "5"


def _ctx():
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    return {"districts": [{"name": "Atherton Community Schools", "short": "Atherton", "rings": [ring]}],
            "city_mills": 13.2394, "district_mills": {"Atherton": 41.86}}


def test_tax_estimate_uses_half_price_and_mills():
    t = bst.tax_estimate(150000, {"short": "Atherton"}, _ctx())
    assert t == {"taxable": 75000, "city": 993, "full": 3140}
    assert bst.tax_estimate(None, None, _ctx()) == {"taxable": None, "city": None, "full": None}
    assert bst.tax_estimate(150000, {"short": "Unknown"}, _ctx())["full"] is None


def test_group_stats_carry_district_and_tax():
    cur = [_sale(0.5, 0.5, 100000, 30 + i) for i in range(5)]
    by_group, _ = bst.assign(cur, _groups())
    stats = bst.group_stats(by_group, _groups(), TODAY, _ctx())
    a, b = stats
    assert a["district"] == "Atherton Community Schools" and a["tax"]["city"] == 662
    assert b["district"] is None and b["tax"]["city"] is None
    fc = bst.build_geojson(stats, TODAY)
    rows = fc["features"][0]["properties"]["_popupRows"]
    assert ["School district", "Atherton Community Schools"] in rows
    assert ["Est. City tax on the median home", "$662 a year"] in rows
    panel = bst.build_panel(cur, stats, 0, TODAY, _ctx())
    labels = {x["label"]: x["value"] for x in panel["stats"]}
    assert labels["Est. City tax on the median home"] == "$662 a year"
    table = panel["tables"][0]
    assert table["columns"][1] == "School district" and table["rows"][0]["cells"][1] == "Atherton"
    assert all(len(r["cells"]) == len(table["columns"]) for r in table["rows"])


def test_short_district_strips_suffixes():
    assert bst.short_district("Carman-Ainsworth Community School District") == "Carman-Ainsworth"
    assert bst.short_district("Bendle Public Schools") == "Bendle"
    assert bst.short_district(None) == "n/a"
