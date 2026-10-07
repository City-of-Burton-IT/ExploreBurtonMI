# Tests for fetch_traffic helpers. No network (get_json is monkeypatched).
# Run: python -m pytest tools/test_fetch_traffic.py -q
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

    def fake(url, params=None, **kw):
        return {"features": mdot if "gisagomdot" in url else county}

    monkeypatch.setattr("lib.arcgis.get_json", fake)
    monkeypatch.setattr(ft, "load_rings", lambda: RINGS)
    monkeypatch.setattr(ft, "OUT_GEOJSON", str(tmp_path / "t.geojson"))
    monkeypatch.setattr(ft, "OUT_SUMMARY", str(tmp_path / "s.json"))
    assert ft.main() == 0
    text = (tmp_path / "t.geojson").read_text(encoding="utf-8")
    assert text.count("\n") == 1 and "_named" not in text and "Main St" in text
