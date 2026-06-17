# Tests for tying funded capital road projects to the Roads (PASER) table.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import capital_roads_link as link  # noqa: E402


def test_normalize_strips_direction_type_and_segment():
    assert link.normalize_road("Genesee Rd (Atherton to Court)") == "genesee"
    assert link.normalize_road("N Genesee Rd") == "genesee"
    assert link.normalize_road("W Court St") == "court"
    assert link.normalize_road("Court St (Genesee to city limits)") == "court"
    assert link.normalize_road("S Grand Traverse St") == "grand traverse"
    assert link.normalize_road("N Grand Traverse (Bristol to Hemphill)") == "grand traverse"
    assert link.normalize_road("Genesee Rd reconstruction (Atherton to Court)") == "genesee"
    assert link.normalize_road("Genesee Rd sidewalk project") == "genesee"
    assert link.normalize_road("Covert Rd") == "covert"


def test_ramps_and_cross_streets_do_not_collapse_to_a_road():
    # an I-69 ramp must not normalize to "belsay" (would be a false match)
    assert link.normalize_road("Belsay/W I 69 RAMP") != "belsay"
    # Atherton is only a cross-street in a Genesee project, never funded itself
    assert link.normalize_road("E Atherton Rd") == "atherton"


def test_funded_keys_only_from_street_categories():
    rows = [
        {"project": "Genesee Rd reconstruction (Atherton to Court)", "category": "Major Streets"},
        {"project": "Burton Estates paving", "category": "Local Streets"},
        {"project": "Two patrol vehicles (Tahoe)", "category": "Facilities & Equipment"},
    ]
    keys = link.funded_keys(rows)
    assert "genesee" in keys
    assert "burton estates" in keys
    assert all("tahoe" not in k for k in keys)   # equipment never becomes a road key


def test_parse_section():
    assert link.parse_section("Genesee Rd (Atherton to Court)") == ("Atherton", "Court")
    assert link.parse_section("Covert Rd (Davison to city limits)") == ("Davison", "city limits")
    assert link.parse_section("Genesee Rd sidewalk project") is None


# A straight E-W "Main St" of three block segments; two cross-streets sit exactly on the
# inner vertices, so the section "First to Second" is just the middle block.
def _paser_fixture():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "Main St"},
         "geometry": {"type": "LineString", "coordinates": [[-83.00, 43.0], [-83.01, 43.0]]}},
        {"type": "Feature", "properties": {"name": "Main St"},
         "geometry": {"type": "LineString", "coordinates": [[-83.01, 43.0], [-83.02, 43.0]]}},
        {"type": "Feature", "properties": {"name": "Main St"},
         "geometry": {"type": "LineString", "coordinates": [[-83.02, 43.0], [-83.03, 43.0]]}},
        {"type": "Feature", "properties": {"name": "First Ave"},
         "geometry": {"type": "LineString", "coordinates": [[-83.01, 42.99], [-83.01, 43.01]]}},
        {"type": "Feature", "properties": {"name": "Second Ave"},
         "geometry": {"type": "LineString", "coordinates": [[-83.02, 42.99], [-83.02, 43.01]]}},
    ]}


def test_build_overlay_clips_to_named_section():
    rows = [{"project": "Main St (First to Second)", "category": "Major Streets", "amount": "500000"}]
    fc = link.build_overlay(_paser_fixture(), rows)
    coords = [f["geometry"]["coordinates"] for f in fc["features"]]
    assert coords == [[[-83.01, 43.0], [-83.02, 43.0]]]    # only the middle block
    f = fc["features"][0]
    assert f["properties"]["_color"] == link._FUNDED_COLOR
    assert ["Project", "Main St (First to Second)"] in f["properties"]["_popupRows"]


def test_build_overlay_skips_unsectioned_and_unmatched_projects():
    rows = [
        {"project": "Main St sidewalk project", "category": "Major Streets", "amount": "100000"},  # no section
        {"project": "Industrial Parks road project", "category": "Major Streets", "amount": "2000000"},  # no road match
        {"project": "Two patrol vehicles", "category": "Facilities & Equipment", "amount": "140000"},  # not a street
    ]
    fc = link.build_overlay(_paser_fixture(), rows)
    assert fc["features"] == []    # nothing drawn (no whole-road fallback)


def test_annotate_flags_matching_rows_and_is_idempotent():
    table = {
        "title": "Federal-aid roads in Burton",
        "columns": ["Road", "Condition", "Miles", "Daily traffic"],
        "rows": [
            {"cells": ["N Genesee Rd", "Poor", "5.82", "11,568"], "color": "#c0392b"},
            {"cells": ["S Center Rd", "Fair", "3.62", "35,043"], "color": "#e08a00"},
            {"cells": ["Covert Rd", "Poor", "0.80", "2,268"], "color": "#c0392b"},
        ],
    }
    funded = {"genesee", "covert"}
    out, n = link.annotate_table(table, funded)
    assert out["columns"] == ["Road", "Condition", "Miles", "Daily traffic", "Improvement"]
    assert n == 2
    assert out["rows"][0]["cells"][-1] == "Funded FY2026-27"   # Genesee
    assert out["rows"][1]["cells"][-1] == ""                    # Center (not funded)
    assert out["rows"][2]["cells"][-1] == "Funded FY2026-27"    # Covert
    # idempotent: running again does not add a second Improvement column
    out2, n2 = link.annotate_table(out, funded)
    assert out2["columns"].count("Improvement") == 1
    assert out2["rows"][0]["cells"] == out["rows"][0]["cells"]
    assert n2 == 2
