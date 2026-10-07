# Tests for fetch_traffic helpers. No network (get_json is monkeypatched).
# Run: python -m pytest tools/test_fetch_traffic.py -q
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fetch_traffic as ft  # noqa: E402

# ~0.8 km x 1.1 km box near Burton: lon -83.64..-83.63, lat 43.00..43.01
RINGS = [[[-83.64, 43.00], [-83.63, 43.00], [-83.63, 43.01], [-83.64, 43.01], [-83.64, 43.00]]]


def seg(coords, aadt=3000, com=150, year="2025", program="STATE"):
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"Aadt": aadt, "AadtCommercial": com, "Year": year, "Program": program}}


INSIDE = [[-83.638, 43.005], [-83.632, 43.005]]
OUTSIDE = [[-83.60, 43.02], [-83.59, 43.02]]


@pytest.mark.parametrize("aadt,band", [(0, "<2k"), (1999, "<2k"), (2000, "2k-5k"), (4999, "2k-5k"),
                                       (5000, "5k-10k"), (9999, "5k-10k"), (10000, "10k-20k"),
                                       (19999, "10k-20k"), (20000, "20k+"), (50000, "20k+")])
def test_band_for(aadt, band):
    assert ft.band_for(aadt) == band


def test_haversine_one_degree_latitude():
    assert ft.haversine_m([0, 0], [0, 1]) == pytest.approx(111195, rel=0.002)


def test_clip_keeps_inside_drops_outside_and_keeps_crossing_vertex():
    crossing = [[-83.645, 43.005], [-83.635, 43.005], [-83.60, 43.005]]  # one vertex inside
    feats = ft.build_features([seg(INSIDE), seg(OUTSIDE), seg(crossing)], RINGS, [])
    assert len(feats) == 2
    assert all(f["properties"]["length_m"] > 0 for f in feats)


def test_properties_trucks_year_band_and_unnamed_label():
    f = ft.build_features([seg(INSIDE, aadt=12000, com=600)], RINGS, [])[0]["properties"]
    assert (f["aadt"], f["trucks_pct"], f["year"], f["band"]) == (12000, 5, 2025, "10k-20k")
    assert f["name"] == "Road segment" and f["_named"] is False
    assert f["_popupRows"][0] == ["Daily vehicles", "12,000"]
    none = ft.build_features([seg(INSIDE, com=None)], RINGS, [])[0]["properties"]
    assert none["trucks_pct"] is None


def test_nearest_name_within_and_beyond_150m_any_vertex():
    verts = [[-83.638, 43.005], [-83.632, 43.005]]
    # 0.001 deg lon at lat 43 is about 81 m; 0.003 deg is about 244 m
    near = (-83.632 + 0.001, 43.005, "Near Rd", None)      # near the LAST vertex only
    nearer = (-83.632 + 0.0005, 43.005, "Nearer Rd", None)
    far = (-83.632 + 0.003, 43.005, "Far Rd", None)
    assert ft.nearest_name(verts, [far, near]) == "Near Rd"
    assert ft.nearest_name(verts, [near, nearer]) == "Nearer Rd"  # smallest distance wins
    assert ft.nearest_name(verts, [far]) is None


def test_clean_name_normalises():
    assert ft.clean_name("  S.  Saginaw ") == "S Saginaw"
    assert ft.clean_name("CENTER RD") == "Center Rd"
    assert ft.clean_name("McKinley Rd") == "McKinley Rd"


def test_build_features_names_from_vertex_match():
    near = (-83.632 + 0.001, 43.005, "Near Rd", 3000)  # ~81 m from the last vertex, ~330 m from midpoint
    f = ft.build_features([seg(INSIDE)], RINGS, [near])[0]["properties"]
    assert f["name"] == "Near Rd" and f["_named"] is True


def test_ratio_rule_pass_and_fail():
    verts = [[-83.638, 43.005], [-83.632, 43.005]]
    cross = (-83.6378, 43.005, "Cross St", 1000)   # nearest (~16 m) but 1000 vs 12000: fails
    same = (-83.6372, 43.005, "Same Rd", 6000)     # ~50 m, 6000 vs 12000 = 0.5: passes
    assert ft.nearest_name(verts, [cross, same], 12000) == "Same Rd"
    assert ft.nearest_name(verts, [cross], 12000) is None
    assert ft.nearest_name(verts, [cross], 2000) == "Cross St"   # 0.5 ratio passes
    assert ft.ratio_ok(5001, 2000) is False and ft.ratio_ok(5000, 2000) is True


PARALLEL = ("Parallel Rd", [[-83.639, 43.00515], [-83.631, 43.00515]])  # ~17 m north
CROSSING = ("Cross St", [[-83.635, 43.000], [-83.635, 43.010]])          # through the midpoint
FAR = ("Far Ave", [[-83.639, 43.0060], [-83.631, 43.0060]])            # ~110 m north


def test_seg_dist_and_bearing_helpers():
    assert ft.seg_dist_m([-83.635, 43.005], [-83.64, 43.005], [-83.63, 43.005]) < 1
    assert abs(ft.seg_dist_m([-83.635, 43.0059], [-83.64, 43.005], [-83.63, 43.005]) - 100) < 2
    assert abs(ft.bearing_deg([-83.64, 43.0], [-83.63, 43.0]) - 90) < 0.01
    assert ft.bearing_deg([-83.635, 43.0], [-83.635, 43.01]) < 0.01
    assert ft.bearing_diff(5, 175) == 10 and ft.bearing_diff(90, 60) == 30


def test_nearest_line_name_prefers_parallel_within_radius_over_crossing_and_far():
    geom = {"type": "LineString", "coordinates": INSIDE}
    assert ft.nearest_line_name(geom, [CROSSING, FAR, PARALLEL]) == "Parallel Rd"
    assert ft.nearest_line_name(geom, [CROSSING, FAR]) is None
    assert ft.nearest_line_name(geom, [FAR], radius=200) == "Far Ave"
    assert ft.nearest_line_name({"type": "LineString", "coordinates": []}, [PARALLEL]) is None


def test_build_features_uses_line_sources_in_order_before_points_and_marks_named():
    pts = [(-83.6378, 43.005, "County Name", None)]
    nearer = ("Nearer Rd", [[-83.639, 43.00505], [-83.631, 43.00505]])  # ~6 m: closer than PARALLEL
    f = ft.build_features([seg(INSIDE, program="LR")], RINGS, pts, [[PARALLEL]])[0]["properties"]
    assert f["name"] == "Parallel Rd" and f["_named"] is True
    s = ft.build_features([seg(INSIDE, program="LR")], RINGS, pts, [[PARALLEL], [nearer]])[0]["properties"]
    assert s["name"] == "Parallel Rd"  # first source wins even when a later one is nearer
    g = ft.build_features([seg(INSIDE, program="LR")], RINGS, pts, [[CROSSING], []])[0]["properties"]
    assert g["name"] == "County Name"
    h = ft.build_features([seg(INSIDE, program="LR")], RINGS, [], [[CROSSING]])[0]["properties"]
    assert h["name"] == "Local road segment" and h["_named"] is False
    r = ft.build_features([seg(INSIDE, program="RMP")], RINGS, [], [[PARALLEL]])[0]["properties"]
    assert r["name"] == "Parallel Rd ramp"
    r2 = ft.build_features([seg(INSIDE, program="RMP")], RINGS, [], [[("X / I-69 ramp", PARALLEL[1])]])
    assert r2[0]["properties"]["name"] == "X / I-69 ramp"


@pytest.mark.parametrize("raw,want", [
    ("E I 69", "I-69"), ("N I 475", "I-475"), ("Belsay/E I 69 RAMP", "Belsay / I-69 ramp"),
    ("W I 69/Center RAMP", "I-69 / Center ramp"), ("S Belsay Rd", "S Belsay Rd"),
    ("  N  Dort   Hwy ", "N Dort Hwy"), (None, ""),
])
def test_tidy_paser_name(raw, want):
    assert ft.tidy_paser_name(raw) == want


def test_osm_display_name_and_lines():
    assert ft.osm_display_name({"highway": "motorway", "ref": "I 69", "name": "Chevrolet-Buick Freeway"}) == "I-69"
    assert ft.osm_display_name({"highway": "motorway_link", "ref": "I 475;I 69"}) == "I-475"
    assert ft.osm_display_name({"highway": "residential", "ref": "X", "name": "Howe  Road"}) == "Howe Road"
    assert ft.osm_display_name({"highway": "residential"}) is None
    els = [{"type": "way", "tags": {"highway": "residential", "name": "A St"},
            "geometry": [{"lon": -83.64, "lat": 43.0}, {"lon": -83.63, "lat": 43.0}]},
           {"type": "node", "tags": {"name": "ignored"}},
           {"type": "way", "tags": {"highway": "service"}, "geometry": [{"lon": 0, "lat": 0}]}]
    assert ft.osm_lines(els) == [("A St", [[-83.64, 43.0], [-83.63, 43.0]])]


def test_paser_lines_reads_file_and_tolerates_absence(tmp_path):
    p = tmp_path / "paser.geojson"
    p.write_text('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name":"E I 69"},'
                 '"geometry":{"type":"LineString","coordinates":[[-83.64,43.0],[-83.63,43.0]]}}]}',
                 encoding="utf-8")
    assert ft.paser_lines(str(p)) == [("I-69", [[-83.64, 43.0], [-83.63, 43.0]])]
    assert ft.paser_lines(str(tmp_path / "missing.geojson")) == []


def test_year_flag_and_mdot_url():
    assert ft.parse_args([]).year == ft.DEFAULT_YEAR
    assert ft.parse_args(["--year", "2026"]).year == 2026
    assert ft.mdot_url(2026).endswith("MdotAadtCaadt2026/FeatureServer/0/query")
    s = ft.summarize(ft.build_features([seg(INSIDE)], RINGS, []), 2026)
    assert s["mdot_year"] == 2026 and "AADT 2026" in s["_source"]


def test_fallback_labels_and_kept_properties():
    f1 = ft.build_features([seg(INSIDE, program="TL")], RINGS, [])[0]["properties"]
    f2 = ft.build_features([seg(INSIDE, program="LR")], RINGS, [])[0]["properties"]
    f3 = ft.build_features([seg(INSIDE, program="XX")], RINGS, [])[0]["properties"]
    assert (f1["name"], f2["name"], f3["name"]) == (
        "State highway segment", "Local road segment", "Road segment")
    assert f1["program"] == "TL" and "facility_type" in f1


def test_guard_refuses_small_and_short():
    feats = ft.build_features([seg(INSIDE)] * 3, RINGS, [])
    with pytest.raises(SystemExit):
        ft.check_guards(feats, ft.summarize(feats))
    many = ft.build_features([seg(INSIDE)] * 120, RINGS, [])  # 120 x ~0.5 km = ~37 mi
    ft.check_guards(many, ft.summarize(many))  # passes
    short = ft.build_features([seg([[-83.638, 43.005], [-83.6379, 43.005]])] * 120, RINGS, [])
    with pytest.raises(SystemExit):
        ft.check_guards(short, ft.summarize(short))


def test_summary_busiest_excludes_unnamed_and_median():
    names = [(-83.6378, 43.005, "Main St", None)]  # ~16 m from the first vertex
    far = [[-83.638, 43.008], [-83.632, 43.008]]  # >150 m from the county point -> unnamed
    feats = ft.build_features([seg(INSIDE, aadt=500), seg(far, aadt=9000)], RINGS, names)
    s = ft.summarize(feats)
    assert [b["name"] for b in s["busiest"]] == ["Main St"]
    assert s["busiest"][0]["aadt"] == 500  # the 9,000 segment is unnamed so excluded
    assert s["years"] == {"min": 2025, "max": 2025}
    assert s["median_aadt"] == 4750


def test_main_end_to_end_with_monkeypatched_get_json(monkeypatch, tmp_path):
    mdot = [seg(INSIDE)] * 120
    county = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-83.6378, 43.005]},
               "properties": {"ON_ROAD": "MAIN ST", "AADT": 3000}}]

    osm = {"elements": [{"type": "way", "tags": {"highway": "residential", "name": "Side Street"},
                         "geometry": [{"lon": -83.639, "lat": 43.0060}, {"lon": -83.631, "lat": 43.0060}]}]}

    def fake(url, params=None, **kw):
        if "overpass" in url:
            assert "MdotAadtCaadt" not in url and 'way["highway"]' in params["data"]
            return osm
        if "gisagomdot" in url:
            assert "MdotAadtCaadt2024" in url
            return {"features": mdot}
        return {"features": county}

    monkeypatch.setattr("lib.arcgis.get_json", fake)
    monkeypatch.setattr(ft, "get_json", fake)
    monkeypatch.setattr(ft, "PASER_ROADS", str(tmp_path / "no-paser.geojson"))
    monkeypatch.setattr(ft, "load_rings", lambda: RINGS)
    monkeypatch.setattr(ft, "OUT_GEOJSON", str(tmp_path / "t.geojson"))
    monkeypatch.setattr(ft, "OUT_SUMMARY", str(tmp_path / "s.json"))
    assert ft.main(["--year", "2024"]) == 0
    text = (tmp_path / "t.geojson").read_text(encoding="utf-8")
    assert text.count("\n") == 1 and "_named" not in text and "Main St" in text
    assert "Side Street" not in text  # the OSM way is 110 m away: county point wins
    summary = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    assert summary["mdot_year"] == 2024 and "AADT 2024" in summary["_source"]
