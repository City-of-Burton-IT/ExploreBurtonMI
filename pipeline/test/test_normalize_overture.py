import json

import pytest

from src.normalize_overture import (
    match_rule_category,
    normalize_feature,
    normalize_overture,
    filter_residential,
    is_residential,
    load_snapshot,
)

CATEGORY_MAP = {
    "_default": "Professional & Personal Services",
    "rules": [
        {"category": "Grocery & Food", "keywords": ["grocery", "bakery"]},
        {"category": "Dining", "exact": ["bar"], "keywords": ["restaurant", "coffee"]},
        {"category": "Automotive", "keywords": ["auto", "car_wash"]},
        {"category": "Retail & Shopping", "keywords": ["store", "jewelry"]},
        {"category": "Professional & Personal Services", "keywords": ["barber"]},
    ],
}


def test_exact_match_beats_substring_collision():
    # 'bar' exactly -> Dining; 'barber_shop' must NOT be pulled into Dining by 'bar'
    assert match_rule_category("bar", CATEGORY_MAP) == "Dining"
    assert match_rule_category("barber_shop", CATEGORY_MAP) == "Professional & Personal Services"


def _feat(fid="abc123", name="Place", overture_category="restaurant",
          confidence=0.9, lng=-83.62, lat=43.0, **props):
    p = {"name": name, "overture_category": overture_category, "confidence": confidence}
    p.update(props)
    return {
        "type": "Feature",
        "id": fid,
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": p,
    }


# --- match_rule_category ----------------------------------------------------

def test_match_keyword_substring():
    assert match_rule_category("mexican_restaurant", CATEGORY_MAP) == "Dining"


def test_match_first_rule_wins_by_order():
    # 'bakery' is in Grocery (listed before Dining); a bakery_cafe still hits Grocery first
    assert match_rule_category("bakery_cafe", CATEGORY_MAP) == "Grocery & Food"


def test_no_rule_match_returns_none():
    assert match_rule_category("tattoo_parlor", CATEGORY_MAP) is None


# --- normalize_feature ------------------------------------------------------

def test_maps_category_and_prefixes_id():
    f = normalize_feature(_feat(fid="0xdeadbeef", overture_category="coffee_shop"), CATEGORY_MAP)
    assert f["id"] == "overture:0xdeadbeef"
    assert f["properties"]["category"] == "Dining"
    assert f["geometry"]["coordinates"] == [-83.62, 43.0]


def test_unmapped_uses_default():
    f = normalize_feature(_feat(overture_category="tattoo_parlor"), CATEGORY_MAP)
    assert f["properties"]["category"] == "Professional & Personal Services"


def test_unmapped_dropped_when_default_is_null():
    cmap = {"_default": None, "rules": CATEGORY_MAP["rules"]}
    assert normalize_feature(_feat(overture_category="tattoo_parlor"), cmap) is None


def test_below_confidence_dropped():
    assert normalize_feature(_feat(confidence=0.3), CATEGORY_MAP, min_confidence=0.5) is None


def test_missing_confidence_kept():
    f = _feat()
    del f["properties"]["confidence"]
    assert normalize_feature(f, CATEGORY_MAP, min_confidence=0.5) is not None


def test_unnamed_dropped():
    assert normalize_feature(_feat(name="  "), CATEGORY_MAP) is None


def test_non_point_dropped():
    f = _feat()
    f["geometry"] = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
    assert normalize_feature(f, CATEGORY_MAP) is None


def test_only_allowlisted_props_emitted():
    f = normalize_feature(
        _feat(address="100 Center Rd, Burton, MI 48519", phone="810-555-1212",
              website="https://x.example", confidence=0.9, revenue="SECRET",
              employee_size="10"),
        CATEGORY_MAP,
    )
    assert set(f["properties"]) == {"name", "category", "address", "phone", "website"}
    assert "revenue" not in f["properties"]
    assert "confidence" not in f["properties"]


def test_empty_optional_props_omitted():
    f = normalize_feature(_feat(address="", phone=None), CATEGORY_MAP)
    assert "address" not in f["properties"]
    assert "phone" not in f["properties"]


# --- normalize_overture (batch + stats) -------------------------------------

def test_batch_returns_features_and_default_count():
    feats = [
        _feat(fid="1", overture_category="restaurant"),       # Dining
        _feat(fid="2", overture_category="tattoo_parlor"),    # default
        _feat(fid="3", overture_category="jewelry_store"),    # Retail
        _feat(fid="4", name="", overture_category="restaurant"),  # dropped (no name)
    ]
    out, defaulted = normalize_overture(feats, CATEGORY_MAP)
    assert len(out) == 3
    assert defaulted == 1
    assert [x["id"] for x in out] == ["overture:1", "overture:2", "overture:3"]


# --- load_snapshot ----------------------------------------------------------

def test_residential_filter_drops_home_prone_and_keeps_storefronts():
    excl = ["lawn", "handyman", "roofing"]
    feats = [
        _feat(fid="1", overture_category="lawn_care_service"),   # dropped
        _feat(fid="2", overture_category="handyman"),            # dropped
        _feat(fid="3", overture_category="restaurant"),          # kept
        _feat(fid="4", overture_category="grocery_store"),       # kept
    ]
    kept, removed = filter_residential(feats, excl)
    assert removed == 2
    assert [f["id"] for f in kept] == ["3", "4"]


def test_name_hint_overrides_overture_category():
    cmap = {
        "_default": "Professional & Personal Services",
        "name_hints": [{"category": "Education", "keywords": ["daycare", "child_care"]}],
        "rules": [{"category": "Professional & Personal Services", "keywords": ["home_service"]}],
    }
    # day-care mis-tagged 'home_service' -> the NAME hint wins -> Education
    daycare = normalize_feature(_feat(name="Doodle Bugs Daycare", overture_category="home_service"), cmap)
    assert daycare["properties"]["category"] == "Education"
    # a genuine home_service with no childcare name falls back to the category code
    cleaner = normalize_feature(_feat(name="Bob's Cleaning", overture_category="home_service"), cmap)
    assert cleaner["properties"]["category"] == "Professional & Personal Services"


def test_skip_categories_drops_civic_mapped_features():
    # A feature mapping to a skipped Burton category (curated layer owns civic) is dropped.
    cmap = {"_default": "Professional & Personal Services",
            "rules": [{"category": "Government", "keywords": ["post_office", "courthouse"]},
                      {"category": "Dining", "keywords": ["restaurant"]}]}
    gov = _feat(fid="g", overture_category="courthouse")
    assert normalize_feature(gov, cmap, skip_categories=("Government",)) is None
    # without the skip, it maps normally
    assert normalize_feature(gov, cmap)["properties"]["category"] == "Government"
    out, _ = normalize_overture([gov, _feat(fid="d", overture_category="restaurant")],
                                cmap, skip_categories=("Government",))
    assert [f["id"] for f in out] == ["overture:d"]


def test_residential_filter_disabled_with_empty_list():
    feats = [_feat(overture_category="lawn_care_service")]
    kept, removed = filter_residential(feats, [])
    assert removed == 0 and len(kept) == 1
    assert is_residential(feats[0], []) is False


def test_load_snapshot_reads_features(tmp_path):
    p = tmp_path / "snap.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [_feat()]}), encoding="utf-8")
    assert len(load_snapshot(str(p))) == 1


def test_load_snapshot_rejects_non_collection(tmp_path):
    p = tmp_path / "bad.geojson"
    p.write_text(json.dumps({"type": "Feature", "geometry": None}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_snapshot(str(p))
