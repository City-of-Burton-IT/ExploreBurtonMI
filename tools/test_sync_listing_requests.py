"""Tests for the pure transforms in sync_listing_requests.py (no network)."""
import json

import sync_listing_requests

from sync_listing_requests import (
    apply_rows,
    parse_coordinates,
    row_to_candidate,
    row_to_override,
)


def fields(**over):
    base = {
        "id": "7",
        "ChangeType": "Fix listing",
        "Title": "Test Cafe",
        "ListingId": "osm:node/1",
        "NewPhone": "(810) 555-0100",
    }
    base.update(over)
    return base


def ovr(f):
    """row_to_override that asserts a result (keeps type checkers happy)."""
    result = row_to_override(f)
    assert result is not None
    return result


def test_parse_coordinates_lat_lng_to_lng_lat():
    assert parse_coordinates("43.002, -83.632") == [-83.632, 43.002]


def test_parse_coordinates_rejects_garbage_and_out_of_range():
    assert parse_coordinates(None) is None
    assert parse_coordinates("") is None
    assert parse_coordinates("not,numbers") is None
    assert parse_coordinates("999, -83.6") is None


def test_fix_listing_maps_new_fields_to_properties():
    listing_id, entry = ovr(fields(NewName="Cafe X", NewHours="Mon-Fri 8-5"))
    assert listing_id == "osm:node/1"
    assert entry["name"] == "Cafe X"
    assert entry["phone"] == "(810) 555-0100"
    assert entry["hours"] == "Mon-Fri 8-5"
    assert "_why" in entry


def test_why_carries_row_number_but_never_contact_pii():
    _, entry = ovr(fields(ContactName="Pat Owner", ContactPhoneEmail="pat@x.com"))
    blob = str(entry)
    assert "row 7" in entry["_why"]
    assert "Pat Owner" not in blob
    assert "pat@x.com" not in blob


def test_closed_becomes_hidden():
    _, entry = ovr(fields(ChangeType="Permanently closed"))
    assert entry["hidden"] is True


def test_moved_with_pin_sets_coordinates():
    _, entry = ovr(
        fields(ChangeType="Moved", NewAddress="1 Main St", NewCoordinates="43.0,-83.6")
    )
    assert entry["coordinates"] == [-83.6, 43.0]
    assert entry["address"] == "1 Main St"
    assert "_todo" not in entry


def test_moved_without_pin_flags_for_geocode():
    _, entry = ovr(fields(ChangeType="Moved", NewAddress="1 Main St", NewPhone=""))
    assert "NEEDS COORDINATES" in entry["_todo"]


def test_add_new_and_missing_listing_id_are_not_auto_applied():
    assert row_to_override(fields(ChangeType="Add my business")) is None
    assert row_to_override(fields(ListingId="")) is None


def test_no_usable_fields_returns_none():
    assert row_to_override(fields(NewPhone="")) is None


def test_candidate_geocodes_by_address_when_no_pin():
    cand = row_to_candidate(fields(ChangeType="Add my business", NewAddress="1 Main St"))
    assert cand["id"] == "burton:test-cafe"
    assert cand["geometry"] is None
    assert cand["properties"]["address"] == "1 Main St"
    assert "_review" in cand


def test_apply_rows_merges_into_existing_override():
    overrides = {"osm:node/1": {"website": "https://old.example"}}
    report = apply_rows([{"fields": fields()}], overrides)
    assert report["applied"] == ["row 7 -> osm:node/1"]
    assert overrides["osm:node/1"]["phone"] == "(810) 555-0100"
    assert overrides["osm:node/1"]["website"] == "https://old.example"


def test_apply_rows_routes_add_new_to_candidates():
    report = apply_rows([{"fields": fields(ChangeType="Add my business")}], {})
    assert len(report["candidates"]) == 1
    assert report["applied"] == []


def test_dispatch_add_new_never_writes_candidate_to_public_repo(tmp_path, monkeypatch):
    overrides = tmp_path / "overrides.json"
    overrides.write_text("{}\n", encoding="utf-8")
    candidates = tmp_path / "pending-additions.json"
    monkeypatch.setattr(sync_listing_requests, "OVERRIDES_PATH", str(overrides))
    monkeypatch.setattr(sync_listing_requests, "CANDIDATES_PATH", str(candidates))

    result = sync_listing_requests.run_from_payload(
        fields(ChangeType="Add my business", NewAddress="1 Main St")
    )

    assert result == 0
    assert json.loads(overrides.read_text(encoding="utf-8")) == {}
    assert not candidates.exists()


def test_dispatch_updates_committed_public_data_without_network(tmp_path, monkeypatch):
    overrides = tmp_path / "overrides.json"
    overrides.write_text("{}\n", encoding="utf-8")
    public_data = tmp_path / "data.geojson"
    public_data.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "osm:node/1",
                        "geometry": {"type": "Point", "coordinates": [-83.6, 43.0]},
                        "properties": {
                            "name": "Test Cafe",
                            "category": "Dining",
                            "phone": "(810) 555-0000",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_listing_requests, "OVERRIDES_PATH", str(overrides))
    monkeypatch.setattr(
        sync_listing_requests, "PUBLIC_DATA_PATH", str(public_data), raising=False
    )

    result = sync_listing_requests.run_from_payload(fields())

    published = json.loads(public_data.read_text(encoding="utf-8"))
    assert result == 0
    assert published["features"][0]["properties"]["phone"] == "(810) 555-0100"
