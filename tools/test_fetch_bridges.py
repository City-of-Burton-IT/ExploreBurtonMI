# Unit tests for fetch_bridges.build_bridges_geojson -- the pure NBI-row -> GeoJSON
# transformation. No network needed. Run: python -m pytest tools/test_fetch_bridges.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fetch_bridges as fb  # noqa: E402


def mk_row(**over) -> dict:
    """A synthetic Burton NBI row. Packed DMS coords resolve to ~ (43.0122, -83.62)."""
    row = {
        "LAT_016": "43004400",     # 43 deg 00' 44.00"  -> 43.0122
        "LONG_017": "083371200",   # 83 deg 37' 12.00"  -> 83.6200 (West)
        "DECK_COND_058": "7",
        "SUPERSTRUCTURE_COND_059": "7",
        "SUBSTRUCTURE_COND_060": "8",
        "CULVERT_COND_062": "N",
        "FACILITY_CARRIED_007": "I-69 EB",
        "FEATURES_DESC_006A": "CENTER RD",
        "ADT_029": "48100",
        "YEAR_BUILT_027": "2003",
        "OWNER_022": "01",
    }
    row.update(over)
    return row


def test_coordinates_are_negative_lon_inside_burton():
    # NBI longitude is West; the emitted x MUST be negative or every bridge lands
    # in Asia. Assert the point sits inside Burton's lon/lat band.
    fc = fb.build_bridges_geojson([mk_row()])
    assert len(fc["features"]) == 1
    lon, lat = fc["features"][0]["geometry"]["coordinates"]
    assert -83.70 < lon < -83.55, f"lon {lon} outside Burton's longitude band"
    assert 42.95 < lat < 43.05, f"lat {lat} outside Burton's latitude band"


def test_good_condition_color():
    f = fb.build_bridges_geojson([mk_row()])["features"][0]  # min(7,7,8) -> Good
    assert f["properties"]["condition"] == "Good"
    assert f["properties"]["_color"] == fb.COND_COLOR["Good"]


def test_fair_and_poor_conditions():
    fair = fb.build_bridges_geojson([mk_row(DECK_COND_058="5")])["features"][0]
    assert fair["properties"]["condition"] == "Fair"
    assert fair["properties"]["_color"] == fb.COND_COLOR["Fair"]
    poor = fb.build_bridges_geojson([mk_row(DECK_COND_058="3")])["features"][0]
    assert poor["properties"]["condition"] == "Poor"
    assert poor["properties"]["_color"] == fb.COND_COLOR["Poor"]


def test_unrated_falls_back_to_gray():
    # No numeric condition columns -> Unrated -> gray fallback, never a KeyError.
    row = mk_row(DECK_COND_058="N", SUPERSTRUCTURE_COND_059="N",
                 SUBSTRUCTURE_COND_060="N", CULVERT_COND_062="N")
    f = fb.build_bridges_geojson([row])["features"][0]
    assert f["properties"]["condition"] == "Unrated"
    assert f["properties"]["_color"] == fb.COND_FALLBACK


def test_name_and_popup_rows():
    f = fb.build_bridges_geojson([mk_row()])["features"][0]
    assert f["properties"]["name"] == "I-69 EB over CENTER RD"
    rows = dict(f["properties"]["_popupRows"])
    assert rows["Condition"] == "Good"
    assert rows["Traffic"] == "48,100/day"
    assert rows["Built"] == "2003"
    assert rows["Maintained by"] == "State"


def test_rows_without_coords_are_skipped():
    fc = fb.build_bridges_geojson([mk_row(LAT_016="0", LONG_017="0")])
    assert fc["features"] == []


def test_cond_pct():
    rows = [mk_row(DECK_COND_058="7"), mk_row(DECK_COND_058="7"),
            mk_row(DECK_COND_058="5"), mk_row(DECK_COND_058="3")]  # 2 Good / 1 Fair / 1 Poor
    assert fb._cond_pct(rows) == {"Good": 50, "Fair": 25, "Poor": 25}


def test_cond_pct_excludes_unrated_from_denominator():
    rated = mk_row(DECK_COND_058="7")
    unrated = mk_row(DECK_COND_058="N", SUPERSTRUCTURE_COND_059="N",
                     SUBSTRUCTURE_COND_060="N", CULVERT_COND_062="N")
    assert fb._cond_pct([rated, unrated]) == {"Good": 100, "Fair": 0, "Poor": 0}


def test_build_bridges_table_sorts_by_traffic_and_colors_condition():
    busy = mk_row(ADT_029="48100", FACILITY_CARRIED_007="I-69 EB", FEATURES_DESC_006A="CENTER RD")
    quiet = mk_row(ADT_029="500", DECK_COND_058="3", FACILITY_CARRIED_007="OAK ST",
                   FEATURES_DESC_006A="CREEK", YEAR_BUILT_027="1965", OWNER_022="04")
    table = fb.build_bridges_table([quiet, busy])
    assert table["columns"] == ["Bridge", "Condition", "Built", "Daily traffic", "Maintained by"]
    # Busiest first.
    assert table["rows"][0]["cells"][0] == "I-69 EB over CENTER RD"
    assert table["rows"][0]["cells"][3] == "48,100"
    # The quiet bridge is Poor + City-maintained, with the Poor color.
    assert table["rows"][1]["cells"] == ["OAK ST over CREEK", "Poor", "1965", "500", "City"]
    assert table["rows"][1]["color"] == fb.COND_COLOR["Poor"]
