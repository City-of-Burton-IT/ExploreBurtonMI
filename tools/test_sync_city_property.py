"""Tests for sync_city_property.py: payload mapping, aliases, the validation gate.
Run: python -m pytest tools/test_sync_city_property.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import sync_city_property as scp  # noqa: E402

PACKET = "https://www.burtonmi.gov/departments/purchasing/offer_form.pdf"


def _item(**kw):
    base = {"Parcel": "59-12-776-262", "Address": "1000 FOXTAIL CT", "Track": {"Value": "No bid"},
            "Status": {"Value": "Available"}, "Price": "12,500", "LotSize": "60 x 120 ft",
            "Zoning": "R-1", "Listed": "2026-09-01T00:00:00Z", "PacketUrl": {"Url": PACKET}}
    base.update(kw)
    return base


def test_rows_from_payload_maps_and_normalises():
    rows = scp.rows_from_payload({"rows": [_item(), _item(Parcel="2", Track="Bid Required", Status="Sale pending",
                                                      Price="", Listed="")]})
    assert rows[0]["track"] == "offer" and rows[0]["status"] == "available"
    assert rows[0]["listed"] == "2026-09-01" and rows[0]["packet_url"] == PACKET
    assert rows[1]["track"] == "bid" and rows[1]["status"] == "pending" and rows[1]["listed"] == ""


def test_blank_items_are_skipped_and_bad_payload_fails():
    assert scp.rows_from_payload({"rows": [{"Title": "", "Address": ""}]}) == []
    with pytest.raises(SystemExit):
        scp.rows_from_payload({"items": []})
    with pytest.raises(SystemExit):
        scp.rows_from_payload({"rows": ["not an object"]})


def test_write_csv_then_builder_reader_accepts(tmp_path):
    rows = scp.rows_from_payload({"rows": [_item(), _item(Parcel="59-99", Address="20 B ST", Track="bid", Price="")]})
    out = tmp_path / "city-property-sales.csv"
    scp.write_csv(rows, str(out))
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0] == ",".join(scp.CSV_COLUMNS)
    validated = scp.bcp.read_rows(str(out))
    assert [r["parcel"] for r in validated] == ["59-12-776-262", "59-99"]


def test_validation_gate_rejects_bad_rows(tmp_path):
    rows = scp.rows_from_payload({"rows": [_item(PacketUrl="http://insecure.example")]})
    out = tmp_path / "c.csv"
    scp.write_csv(rows, str(out))
    with pytest.raises(SystemExit, match="https"):
        scp.bcp.read_rows(str(out))


def test_main_dry_run_leaves_no_file(tmp_path, monkeypatch):
    payload = tmp_path / "p.json"
    payload.write_text(json.dumps({"rows": [_item()]}), encoding="utf-8")
    out = tmp_path / "out.csv"
    monkeypatch.setattr(sys, "argv", ["sync", "--payload-file", str(payload), "--out", str(out), "--dry-run"])
    assert scp.main() == 0
    assert not out.exists() and not (tmp_path / "out.csv.dryrun").exists()
