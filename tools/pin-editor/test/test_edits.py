# Tests for the pin-editor edit-routing core. Pure functions, no IO.
import copy

import pytest

from edits import apply_edits, slugify, unique_manual_id, is_curated


def _facilities(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def _feature(fid, name="Name", category="Government", geometry=None, **props):
    return {
        "type": "Feature",
        "id": fid,
        "geometry": geometry,
        "properties": {"name": name, "category": category, **props},
    }


def _by_id(fc, fid):
    return next((f for f in fc["features"] if f.get("id") == fid), None)


# ---- classification --------------------------------------------------------

@pytest.mark.parametrize("fid,curated", [
    ("burton:city-hall", True),
    ("manual:joes-diner", True),
    ("osm:node/5", False),
    ("osm:way/9", False),
    ("overture:abc123", False),
])
def test_is_curated(fid, curated):
    assert is_curated(fid) is curated


def test_slugify():
    assert slugify("Joe's Diner & Grill") == "joes-diner-grill"
    assert slugify("  Multiple   Spaces ") == "multiple-spaces"


def test_unique_manual_id_suffixes_on_collision():
    existing = {"manual:joes-diner", "manual:joes-diner-2"}
    assert unique_manual_id("Joe's Diner", existing) == "manual:joes-diner-3"
    assert unique_manual_id("Brand New", existing) == "manual:brand-new"


# ---- move ------------------------------------------------------------------

def test_move_curated_sets_facilities_geometry():
    fac = _facilities(_feature("burton:city-hall"))
    ov = {"_comment": "c"}
    fac2, ov2 = apply_edits(fac, ov, [
        {"op": "move", "id": "burton:city-hall", "coordinates": [-83.6, 43.0]},
    ])
    assert _by_id(fac2, "burton:city-hall")["geometry"] == {
        "type": "Point", "coordinates": [-83.6, 43.0],
    }
    assert ov2 == ov  # overrides untouched


def test_move_discovered_writes_coordinates_override():
    fac = _facilities(_feature("burton:city-hall"))
    ov = {"_comment": "c"}
    fac2, ov2 = apply_edits(fac, ov, [
        {"op": "move", "id": "osm:node/5", "coordinates": [-83.6, 43.0]},
    ])
    assert ov2["osm:node/5"]["coordinates"] == [-83.6, 43.0]
    assert fac2 == fac  # facilities untouched


# ---- edit ------------------------------------------------------------------

def test_edit_curated_field_updates_facilities():
    fac = _facilities(_feature("burton:city-hall", phone="old"))
    fac2, _ = apply_edits(fac, {}, [
        {"op": "edit", "id": "burton:city-hall", "fields": {"phone": "(810) 555-0000"}},
    ])
    assert _by_id(fac2, "burton:city-hall")["properties"]["phone"] == "(810) 555-0000"


def test_edit_discovered_field_writes_override():
    fac = _facilities()
    fac2, ov2 = apply_edits(fac, {}, [
        {"op": "edit", "id": "overture:abc", "fields": {"website": "https://x.gov"}},
    ])
    assert ov2["overture:abc"]["website"] == "https://x.gov"


def test_edit_curated_same_value_is_noop():
    fac = _facilities(_feature("burton:city-hall", name="Burton City Hall"))
    ov = {"_comment": "c"}
    fac2, ov2 = apply_edits(fac, ov, [
        {"op": "edit", "id": "burton:city-hall", "fields": {"name": "Burton City Hall"}},
    ])
    assert fac2 == fac and ov2 == ov  # no redundant write


# ---- delete ----------------------------------------------------------------

def test_delete_curated_removes_feature():
    fac = _facilities(_feature("burton:city-hall"), _feature("burton:library"))
    fac2, _ = apply_edits(fac, {}, [{"op": "delete", "id": "burton:city-hall"}])
    assert _by_id(fac2, "burton:city-hall") is None
    assert len(fac2["features"]) == 1


def test_delete_discovered_sets_hidden_override():
    fac2, ov2 = apply_edits(_facilities(), {}, [
        {"op": "delete", "id": "osm:node/9", "why": "Permanently closed"},
    ])
    assert ov2["osm:node/9"] == {"hidden": True, "_why": "Permanently closed"}


def test_delete_discovered_default_why():
    _, ov2 = apply_edits(_facilities(), {}, [{"op": "delete", "id": "osm:node/9"}])
    assert ov2["osm:node/9"]["hidden"] is True
    assert ov2["osm:node/9"]["_why"]  # some non-empty default reason


# ---- add -------------------------------------------------------------------

def test_add_creates_manual_facility():
    fac2, _ = apply_edits(_facilities(), {}, [{
        "op": "add", "name": "Joe's Diner", "category": "Dining",
        "coordinates": [-83.6, 43.0], "fields": {"phone": "(810) 555-1212"},
    }])
    feat = _by_id(fac2, "manual:joes-diner")
    assert feat is not None
    assert feat["geometry"] == {"type": "Point", "coordinates": [-83.6, 43.0]}
    assert feat["properties"]["name"] == "Joe's Diner"
    assert feat["properties"]["category"] == "Dining"
    assert feat["properties"]["phone"] == "(810) 555-1212"


def test_add_slug_collision_suffixes():
    fac = _facilities(_feature("manual:joes-diner", name="Joe's Diner", category="Dining"))
    fac2, _ = apply_edits(fac, {}, [{
        "op": "add", "name": "Joe's Diner", "category": "Dining", "coordinates": [-83.6, 43.0],
    }])
    assert _by_id(fac2, "manual:joes-diner-2") is not None
    assert len(fac2["features"]) == 2


# ---- merge + purity --------------------------------------------------------

def test_multi_edit_same_discovered_pin_merges_into_one_entry():
    fac2, ov2 = apply_edits(_facilities(), {}, [
        {"op": "move", "id": "osm:node/7", "coordinates": [-83.6, 43.0]},
        {"op": "edit", "id": "osm:node/7", "fields": {"name": "Corrected Name"}},
    ])
    assert ov2["osm:node/7"]["coordinates"] == [-83.6, 43.0]
    assert ov2["osm:node/7"]["name"] == "Corrected Name"


def test_inputs_not_mutated():
    fac = _facilities(_feature("burton:city-hall"))
    ov = {"_comment": "c"}
    fac_copy, ov_copy = copy.deepcopy(fac), copy.deepcopy(ov)
    apply_edits(fac, ov, [
        {"op": "move", "id": "burton:city-hall", "coordinates": [-83.6, 43.0]},
        {"op": "delete", "id": "osm:node/1"},
    ])
    assert fac == fac_copy and ov == ov_copy  # originals unchanged (pure)
