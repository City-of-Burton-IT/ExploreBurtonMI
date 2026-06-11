"""Unit tests for the fire-station call-volume map builder (no network/files)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_fire_stations as bfs  # noqa: E402


def _info(rows):
    return {"charts": [{"type": "compare", "title": "Calls by station area: 2025 vs 2015", "rows": rows}]}


def _row(n, y2025, y2015):
    return {"label": f"Station {n} area", "values": [
        {"name": "2025", "value": y2025}, {"name": "2015", "value": y2015}]}


def _places():
    def st(n, lon, lat):
        return {"properties": {"name": f"Burton Fire Station {n}"},
                "geometry": {"type": "Point", "coordinates": [lon, lat]}}
    return {"features": [st(1, -83.67, 42.97), st(2, -83.59, 43.01), st(3, -83.62, 43.03)]}


def test_counts_take_latest_year():
    counts = bfs.station_counts(_info([_row(1, 325, 224), _row(2, 335, 192)]))
    assert counts == {1: {"calls": 325, "year": "2025"}, 2: {"calls": 335, "year": "2025"}}


def test_build_three_features_radius_proportional():
    counts = bfs.station_counts(_info([_row(1, 325, 224), _row(2, 335, 192), _row(3, 96, 59)]))
    coords = bfs.station_coords(_places())
    fc = bfs.build(counts, coords)
    feats = fc["features"]
    assert len(feats) == 3
    # busiest station is the largest radius; radius is monotonic with calls
    radii = {f["properties"]["station"]: f["properties"]["_radius"] for f in feats}
    assert radii["Station 2"] >= radii["Station 1"] > radii["Station 3"]
    # absolute sqrt proportionality: r ~ MAX_R * sqrt(calls/max)
    s3 = next(f for f in feats if f["properties"]["station"] == "Station 3")
    expected = round(bfs.MAX_R * math.sqrt(96 / 335), 1)
    assert s3["properties"]["_radius"] == expected
    # popup rows are [label, value] pairs
    assert all(len(r) == 2 for f in feats for r in f["properties"]["_popupRows"])


def test_missing_station_is_skipped():
    counts = bfs.station_counts(_info([_row(1, 325, 224), _row(2, 335, 192)]))  # no station 3
    coords = bfs.station_coords(_places())  # has 1,2,3
    fc = bfs.build(counts, coords)
    stations = {f["properties"]["station"] for f in fc["features"]}
    assert stations == {"Station 1", "Station 2"}  # only matched stations
