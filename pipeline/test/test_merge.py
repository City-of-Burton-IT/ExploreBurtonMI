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


# --- #83: same-business OSM/Overture pairs whose names differ only by generic words


def test_dedupe_collapses_brand_name_vs_brand_gas_station():
    # OSM 'Sunoco' and Overture 'Sunoco Gas Station' at the same pump -> one pin.
    osm = [_at("osm:node/30", "Sunoco", -83.594719, 43.015887, category="Automotive")]
    overture = [_at("overture:a", "Sunoco Gas Station", -83.594718, 43.015882, category="Automotive", website="https://sunoco.example")]
    out = merge(osm + overture, [], {})
    assert len(out) == 1
    assert out[0]["id"] == "osm:node/30"  # first occurrence (OSM) is kept


def test_dedupe_collapses_article_and_company_suffix_variants():
    pairs = [
        ("The Red Baron", "Red Baron"),
        ("Admiral", "Admiral Petroleum Co"),
        ("Parkside Dental Associates P.C.", "Parkside Dental Associates"),
        ("Marathon", "Marathon Gas"),
    ]
    for i, (a, b) in enumerate(pairs):
        feats = [
            _at(f"osm:node/{i}", a, -83.6300, 43.0100),
            _at(f"overture:{i}", b, -83.6301, 43.0101),  # ~14 m apart
        ]
        assert len(merge(feats, [], {})) == 1, (a, b)


def test_dedupe_backfills_missing_properties_from_dropped_twin():
    osm = [_at("osm:node/31", "Marathon", -83.6300, 43.0100, category="Automotive")]
    overture = [_at("overture:b", "Marathon Gas", -83.6301, 43.0101, category="Automotive",
                    address="123 Main St", website="https://marathon.example")]
    out = merge(osm + overture, [], {})
    assert len(out) == 1
    assert out[0]["properties"]["address"] == "123 Main St"
    assert "website" not in out[0]["properties"]  # identity-bound, never copied
    assert out[0]["properties"]["category"] == "Automotive"


def test_dedupe_backfill_requires_same_category():
    # Two unrelated shops both listed under their plaza's name: collapsed as
    # before, but the survivor must not inherit the other's contact details.
    feats = [
        _at("overture:p1", "The Courtyard", -83.6300, 43.0100, category="Retail & Shopping"),
        _at("overture:p2", "The Courtyard", -83.6301, 43.0101, category="Health", phone="555-0100"),
    ]
    out = merge(feats, [], {})
    assert len(out) == 1
    assert "phone" not in out[0]["properties"]


def test_dedupe_does_not_mutate_input_features():
    osm = [_at("osm:node/32", "Marathon", -83.6300, 43.0100)]
    overture = [_at("overture:c", "Marathon Gas", -83.6301, 43.0101, address="123 Main St")]
    merge(osm + overture, [], {})
    assert "address" not in osm[0]["properties"]


def test_dedupe_keeps_substantive_word_variants_nearby():
    # 'Church' / 'Pharmacy' / 'School' are not generic suffixes: distinct places.
    feats = [
        _at("osm:node/40", "Bristol Road Church", -83.6300, 43.0100, category="Faith"),
        _at("osm:node/41", "Bristol Road", -83.6300, 43.0101, category="Retail & Shopping"),
        _at("osm:node/42", "Marathon", -83.6500, 43.0100),
        _at("osm:node/43", "Marathon Pharmacy", -83.6500, 43.0101),
    ]
    assert len(merge(feats, [], {})) == 4


def test_dedupe_keeps_brand_variants_far_apart():
    # Same brand pair across town stays two pins.
    feats = [
        _at("osm:node/50", "Sunoco", -83.594719, 43.015887),
        _at("overture:d", "Sunoco", -83.594656, 43.010689),  # ~580 m south
    ]
    assert len(merge(feats, [], {})) == 2


def test_dedupe_generic_only_names_never_match_each_other():
    # Two records whose names are nothing but generic words must not collapse.
    feats = [
        _at("osm:node/60", "Gas Station", -83.6300, 43.0100),
        _at("overture:e", "The Station", -83.6300, 43.0101),
    ]
    assert len(merge(feats, [], {})) == 2
