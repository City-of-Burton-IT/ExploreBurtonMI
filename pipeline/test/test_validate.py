import pytest

from src.validate import validate, ValidationError

# bbox = [min_lat, min_lng, max_lat, max_lng]
BBOX = [42.95, -83.70, 43.04, -83.55]


def _feat(fid, props, lng=-83.6, lat=43.0):
    return {"type": "Feature", "id": fid, "geometry": {"type": "Point", "coordinates": [lng, lat]}, "properties": props}


def test_strips_disallowed_properties():
    f = _feat("a", {"name": "X", "category": "Dining", "owner": "SECRET", "wikidata": "Q1"})
    out = validate([f], BBOX)
    assert set(out[0]["properties"].keys()) == {"name", "category"}


def test_rejects_missing_name():
    with pytest.raises(ValidationError, match="name"):
        validate([_feat("b", {"category": "Dining"})], BBOX)


def test_rejects_out_of_bounds():
    with pytest.raises(ValidationError, match="out of bounds"):
        validate([_feat("c", {"name": "Far"}, lng=0, lat=0)], BBOX)


def test_rejects_non_point_geometry():
    bad = {"type": "Feature", "id": "d", "geometry": {"type": "LineString", "coordinates": []}, "properties": {"name": "L"}}
    with pytest.raises(ValidationError, match="non-Point"):
        validate([bad], BBOX)


def test_passes_clean_feature():
    f = _feat("e", {"name": "Good", "category": "Dining", "phone": "555", "website": "https://x.com"})
    out = validate([f], BBOX)
    assert out[0]["properties"]["website"] == "https://x.com"
