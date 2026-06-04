from src.clip import point_in_geometry, clip_features

# A unit square from (0,0) to (10,10)
SQUARE = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
}


def test_point_inside():
    assert point_in_geometry(5, 5, SQUARE) is True


def test_point_outside():
    assert point_in_geometry(15, 5, SQUARE) is False


def test_multipolygon():
    mp = {"type": "MultiPolygon", "coordinates": [SQUARE["coordinates"]]}
    assert point_in_geometry(5, 5, mp) is True
    assert point_in_geometry(-1, -1, mp) is False


def test_clip_features_filters_outside_points():
    feats = [
        {"id": "in", "geometry": {"type": "Point", "coordinates": [5, 5]}},
        {"id": "out", "geometry": {"type": "Point", "coordinates": [50, 50]}},
        {"id": "nogeom", "geometry": None},
    ]
    kept = clip_features(feats, SQUARE)
    assert [f["id"] for f in kept] == ["in"]
