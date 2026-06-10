# Unit tests for extract_paser pure functions (PASER grouping, %, clipping,
# per-road aggregation). No network. Run: python -m pytest tools/test_extract_paser.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_paser as ep  # noqa: E402

# A unit square boundary around (0,0): lon/lat in [0,1].
SQUARE = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]


def feat(rating, miles, name="Main St", adt=0, surf="Asphalt", mid=(0.5, 0.5)):
    """A geojson-style PASER segment whose middle vertex is `mid`."""
    return {
        "properties": {"CURRRATING": rating, "LENGTHMILE": miles, "PRNAME": name,
                       "AADT": adt, "SURFTYPE": surf, "RATINGYEAR": 2024},
        "geometry": {"type": "LineString", "coordinates": [list(mid), list(mid), list(mid)]},
    }


def test_group_boundaries():
    assert ep._group(10) == "Good" and ep._group(8) == "Good"
    assert ep._group(7) == "Fair" and ep._group(5) == "Fair"
    assert ep._group(4) == "Poor" and ep._group(1) == "Poor"
    assert ep._group(0) is None        # 0 = Not Rated
    assert ep._group(None) is None
    assert ep._group("") is None       # non-numeric -> None, not a crash


def test_cond_pct_excludes_not_rated():
    miles = {"Good": 1.0, "Fair": 1.0, "Poor": 2.0, "Not Rated": 10.0}
    # Denominator is rated miles only (4), Not Rated dropped.
    assert ep._cond_pct(miles) == {"Good": 25, "Fair": 25, "Poor": 50}


def test_cond_pct_empty():
    assert ep._cond_pct({"Not Rated": 5.0}) == {}


def test_rep_point_is_middle_vertex():
    g = {"type": "LineString", "coordinates": [[0, 0], [0.5, 0.5], [1, 1]]}
    assert ep._rep_point(g) == [0.5, 0.5]


def test_inside_square():
    assert ep._inside(0.5, 0.5, SQUARE) is True
    assert ep._inside(2.0, 2.0, SQUARE) is False


def test_road_table_weighted_condition_and_sort():
    # Two roads. Busy road: 2 mi rated 8 (Good). Quiet road: 1 mi rated 3 (Poor).
    rows = [
        feat(8, 1.0, name="Center Rd", adt=30000),
        feat(8, 1.0, name="Center Rd", adt=30000),
        feat(3, 1.0, name="Oak St", adt=500),
    ]
    table = ep._road_table(rows)
    assert table["columns"] == ["Road", "Condition", "Miles", "Daily traffic"]
    # Busiest first.
    assert table["rows"][0]["cells"][0] == "Center Rd"
    assert table["rows"][0]["cells"] == ["Center Rd", "Good", "2.00", "30,000"]
    assert table["rows"][0]["color"] == ep.COND_COLOR["Good"]
    oak = table["rows"][1]
    assert oak["cells"] == ["Oak St", "Poor", "1.00", "500"]
    assert oak["color"] == ep.COND_COLOR["Poor"]


def test_road_table_not_rated_when_no_rated_miles():
    table = ep._road_table([feat(0, 1.0, name="Gravel Ln")])
    assert table["rows"][0]["cells"][1] == "Not Rated"
    assert table["rows"][0]["color"] == ep.COND_FALLBACK


def test_surface_series_undefined_becomes_other():
    rows = [feat(8, 1.0, surf="Asphalt"), feat(8, 0.5, surf="Undefined")]
    series = {s["label"]: s["value"] for s in ep._surface_series(rows)}
    assert series.get("Asphalt") == 1.0
    assert series.get("Other") == 0.5
    assert "Undefined" not in series
