"""Tests for build_city_property.py: CSV validation, sold-row pruning, popup and
panel shaping. No network: geocoding is not exercised here (build_address_points
has its own geocoder tests); rows get coordinates set directly.
Run: python -m pytest tools/test_build_city_property.py -q
"""
import csv
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import build_city_property as bcp  # noqa: E402

TODAY = date(2026, 10, 15)
PACKET = "https://www.burtonmi.gov/departments/purchasing/offer_form.pdf"
COLS = bcp.REQUIRED + bcp.OPTIONAL


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def _raw(**kw):
    base = {"parcel": "59-12-776-262", "address": "1000 FOXTAIL CT", "track": "offer",
            "price": "12,500", "lot_size": "60 x 120 ft", "zoning": "R-1",
            "status": "available", "listed": "2026-09-01", "packet_url": PACKET}
    base.update(kw)
    return base


def test_read_rows_parses_and_normalises(tmp_path):
    p = tmp_path / "s.csv"
    _write_csv(p, [_raw(), _raw(parcel="59-99", address="VACANT E BRISTOL RD", track="BID",
                                price="", status="Available")])
    rows = bcp.read_rows(str(p))
    assert len(rows) == 2
    assert rows[0]["price"] == 12500
    assert rows[0]["listed"] == date(2026, 9, 1)
    assert rows[1]["track"] == "bid" and rows[1]["status"] == "available"
    assert rows[1]["price"] is None


def test_read_rows_allows_empty_list(tmp_path):
    p = tmp_path / "s.csv"
    _write_csv(p, [])
    assert bcp.read_rows(str(p)) == []


@pytest.mark.parametrize("bad", [
    {"track": "auction"},
    {"status": "maybe"},
    {"packet_url": "http://insecure.example"},
    {"status": "sold"},                       # sold without sold_date
    {"price": "twelve"},
    {"listed": "9/1/2026"},
])
def test_read_rows_fails_loud_on_bad_values(tmp_path, bad):
    p = tmp_path / "s.csv"
    _write_csv(p, [_raw(**bad)])
    with pytest.raises(SystemExit):
        bcp.read_rows(str(p))


def test_read_rows_rejects_duplicate_parcel_and_missing_column(tmp_path):
    p = tmp_path / "s.csv"
    _write_csv(p, [_raw(), _raw(address="OTHER ST")])
    with pytest.raises(SystemExit, match="twice"):
        bcp.read_rows(str(p))
    q = tmp_path / "t.csv"
    q.write_text("parcel,address\n1,2\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing columns"):
        bcp.read_rows(str(q))


def _rows(tmp_path, raws):
    p = tmp_path / "s.csv"
    _write_csv(p, raws)
    return bcp.read_rows(str(p))


def test_prune_drops_sales_older_than_a_year_only(tmp_path):
    rows = _rows(tmp_path, [
        _raw(parcel="1"),
        _raw(parcel="2", status="sold", sold_date="2026-01-15", sold_price="9000"),
        _raw(parcel="3", status="sold", sold_date="2025-06-01", sold_price="9000"),
    ])
    kept = bcp.prune_old_sales(rows, TODAY)
    assert [r["parcel"] for r in kept] == ["1", "2"]


def test_geojson_skips_rows_without_coords_or_outside_city(tmp_path):
    rows = _rows(tmp_path, [_raw(parcel="in"), _raw(parcel="out"), _raw(parcel="none")])
    rows[0].update(lat=43.0, lng=-83.6)
    rows[1].update(lat=10.0, lng=10.0)
    square = [[[-84.0, 42.5], [-83.0, 42.5], [-83.0, 43.5], [-84.0, 43.5], [-84.0, 42.5]]]
    fc, nocoord, outside = bcp.build_geojson(rows, square)
    assert [f["properties"]["parcel"] for f in fc["features"]] == ["in"]
    assert (nocoord, outside) == (1, 1)
    props = fc["features"][0]["properties"]
    assert props["_color"] == bcp.COLORS["available"]
    assert props["name"] == "1000 Foxtail Ct"
    assert all(len(r) == 2 for r in props["_popupRows"])
    assert ["Asking price", "$12,500"] in props["_popupRows"]


def test_popup_rows_for_bid_and_sold(tmp_path):
    rows = _rows(tmp_path, [
        _raw(parcel="b", track="bid", price=""),
        _raw(parcel="s", status="sold", sold_date="2026-08-01", sold_price="15000"),
    ])
    assert ["Minimum bid", "Sealed bid"] in bcp.popup_rows(rows[0])
    assert ["Sold", "$15,000 on 2026-08-01"] in bcp.popup_rows(rows[1])


def test_panel_counts_and_tables(tmp_path):
    rows = _rows(tmp_path, [
        _raw(parcel="1", price="12500"),
        _raw(parcel="2", address="20 B ST", price="8000"),
        _raw(parcel="3", address="30 C ST", track="bid", price=""),
        _raw(parcel="4", address="40 D ST", status="pending"),
        _raw(parcel="5", address="50 E ST", status="sold", sold_date="2026-08-01", sold_price="15000",
             packet_url="https://www.burtonmi.gov/other.pdf"),
    ])
    panel = bcp.build_panel(rows, TODAY)
    stats = {s["label"]: s["value"] for s in panel["stats"]}
    assert stats["Parcels available now"] == "3"
    assert stats["Fixed-price (no bid) parcels"] == "2"
    assert stats["Sealed-bid parcels"] == "1"
    assert stats["Lowest asking price"] == "$8,000"
    assert stats["Sold in the last 12 months"] == "1"
    assert panel["lastUpdated"] == "2026-10-15"
    main, sold = panel["tables"]
    assert len(main["rows"]) == 4 and all(len(r["cells"]) == len(main["columns"]) for r in main["rows"])
    assert sold["rows"][0]["cells"][2] == "$15,000"
    hrefs = [l["href"] for l in panel["links"]]
    assert PACKET in hrefs and "https://www.burtonmi.gov/other.pdf" not in hrefs  # sold packet not linked
    assert len(hrefs) == len(set(hrefs))


def test_panel_empty_list_is_honest():
    panel = bcp.build_panel([], TODAY)
    assert panel["stats"][0]["value"] == "0"
    assert panel["tables"][0]["rows"] == []
    assert "confirming the current list" in panel["notes"][0]
