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


# --- offMap: curated entries whose real location is outside the city -----------
# (e.g. a permit-issued service at an out-of-town facility). They are listed and
# searchable but not plotted on the locked city map. The bypass is ONLY the
# in-bounds check; name, the property allowlist, and Point validity still apply,
# and the flag can only ever be set on hand-curated facilities (never OSM/Overture).

def _offmap(fid, props, lng=-83.842, lat=43.177):  # Montrose, outside BBOX
    f = _feat(f"burton:{fid}", props, lng=lng, lat=lat)
    f["offMap"] = True
    return f


def test_offmap_bypasses_out_of_bounds():
    out = validate([_offmap("dump", {"name": "Brent Run Landfill", "category": "Government"})], BBOX)
    assert len(out) == 1
    assert out[0]["offMap"] is True
    assert out[0]["properties"]["name"] == "Brent Run Landfill"


def test_offmap_still_requires_name():
    with pytest.raises(ValidationError, match="name"):
        validate([_offmap("dump", {"category": "Government"})], BBOX)


def test_offmap_still_strips_disallowed_properties():
    out = validate([_offmap("dump", {"name": "X", "owner": "SECRET"})], BBOX)
    assert set(out[0]["properties"].keys()) == {"name"}


def test_offmap_still_requires_point():
    bad = {"type": "Feature", "id": "burton:dump", "offMap": True,
           "geometry": {"type": "LineString", "coordinates": []}, "properties": {"name": "X"}}
    with pytest.raises(ValidationError, match="non-Point"):
        validate([bad], BBOX)


def test_offmap_ignored_on_non_curated_id():
    # An auto-sourced (non 'burton:') record must NOT use offMap to escape the
    # bounds check - the flag is only honored on hand-curated facility ids.
    sneaky = {"type": "Feature", "id": "overture:evil", "offMap": True,
              "geometry": {"type": "Point", "coordinates": [-83.842, 43.177]},  # outside BBOX
              "properties": {"name": "Sneaky"}}
    with pytest.raises(ValidationError, match="out of bounds"):
        validate([sneaky], BBOX)


def test_non_offmap_feature_does_not_carry_flag():
    out = validate([_feat("e", {"name": "In Town"})], BBOX)
    assert "offMap" not in out[0]
