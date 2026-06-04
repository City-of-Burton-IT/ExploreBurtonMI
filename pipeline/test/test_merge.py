from src.merge import merge, apply_override


def _feat(fid, name, **props):
    p = {"name": name}
    p.update(props)
    return {"type": "Feature", "id": fid, "geometry": {"type": "Point", "coordinates": [-83.6, 43.0]}, "properties": p}


def test_curated_facility_wins_over_osm_duplicate():
    facilities = [_feat("burton:city-hall", "Burton City Hall", category="Government")]
    osm = [_feat("osm:node/1", "Burton City Hall", category="Dining")]
    out = merge(osm, facilities, {})
    assert len(out) == 1
    assert out[0]["id"] == "burton:city-hall"


def test_override_corrects_property():
    osm = [_feat("osm:node/5", "Joe's", category="Retail & Shopping")]
    out = merge(osm, [], {"osm:node/5": {"category": "Dining", "phone": "555"}})
    assert out[0]["properties"]["category"] == "Dining"
    assert out[0]["properties"]["phone"] == "555"


def test_override_hides_record():
    osm = [_feat("osm:node/6", "Closed Shop")]
    out = merge(osm, [], {"osm:node/6": {"hidden": True}})
    assert out == []


def test_override_sets_coordinates():
    f = _feat("burton:x", "X")
    out = apply_override(f, {"coordinates": [-83.5, 43.1]})
    assert out["geometry"]["coordinates"] == [-83.5, 43.1]


def test_comment_key_ignored():
    osm = [_feat("osm:node/7", "Real")]
    # a _comment key in overrides must not match any feature id
    out = merge(osm, [], {"_comment": "note"})
    assert len(out) == 1


def _at(fid, name, lon, lat, **props):
    p = {"name": name}
    p.update(props)
    return {"type": "Feature", "id": fid, "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": p}


def test_dedupe_collapses_same_name_at_same_site():
    # Gas station double-tagged: fuel node (Automotive) + convenience node
    # (Grocery) ~33 m apart -> one marker, not two.
    osm = [
        _at("osm:node/10", "Speedway", -83.6300, 43.0100, category="Automotive"),
        _at("osm:node/11", "Speedway", -83.6300, 43.0103, category="Grocery & Food"),
    ]
    out = merge(osm, [], {})
    assert len(out) == 1


def test_dedupe_keeps_same_name_far_apart():
    # Two genuinely different Speedways across town stay as two markers.
    osm = [
        _at("osm:node/10", "Speedway", -83.6300, 43.0100, category="Automotive"),
        _at("osm:node/11", "Speedway", -83.6600, 42.9700, category="Automotive"),
    ]
    out = merge(osm, [], {})
    assert len(out) == 2


def test_dedupe_keeps_different_names_nearby():
    # A church and its co-located school share a first word but are distinct;
    # must NOT be collapsed.
    osm = [
        _at("osm:way/20", "Blessed Sacrament School", -83.6300, 43.0100, category="Education"),
        _at("osm:way/21", "Blessed Sacrament", -83.6300, 43.0102, category="Faith"),
    ]
    out = merge(osm, [], {})
    assert len(out) == 2
