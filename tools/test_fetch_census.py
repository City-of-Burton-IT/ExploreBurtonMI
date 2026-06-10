# Unit tests for fetch_census.build_panel, the pure ACS-record -> InfoPanel
# transformation. No network/API key needed; build_panel takes a record dict and
# pre-computed trend points. Run: python -m pytest tools/test_fetch_census.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fetch_census as fc  # noqa: E402


def mk_record() -> dict:
    """A synthetic Burton ACS record with deterministic values for assertions."""
    rec = {
        "NAME": "Burton city, Michigan",
        "B01003_001E": "29529",   # population
        "B01002_001E": "42.5",    # median age
        "B11001_001E": "12505",   # households
        "B19013_001E": "57767",   # median household income
        "B25077_001E": "131200",  # median home value
        "B25003_002E": "900",     # owner-occupied
        "B25003_003E": "300",     # renter-occupied -> owner_pct 75%
        "B15003_001E": "1000",    # edu total (25+)
        "B15003_022E": "100", "B15003_023E": "50", "B15003_024E": "20", "B15003_025E": "10",
        "B23025_001E": "2000", "B23025_002E": "1200", "B23025_003E": "1000",
        "B23025_004E": "920", "B23025_005E": "80",     # unemployed 80 / civ LF 1000 -> 8%
        "B17001_001E": "1000", "B17001_002E": "150",   # poverty 15%
        "B21001_001E": "1000", "B21001_002E": "120",   # veterans 12%
    }
    # Fill every grouped member referenced by the panel with a fixed count so the
    # series sums are predictable (each member contributes 10).
    for table, groups in (("B19001", fc.INCOME_GROUPS), ("B15003", fc.EDU_GROUPS),
                          ("B08301", fc.COMMUTE_GROUPS), ("B01001", fc.AGE_BANDS)):
        for _, codes in groups:
            for c in codes:
                rec.setdefault(f"{table}_{c}E", "10")
    return rec


TREND = [{"x": "2010", "y": 30000}, {"x": "2020", "y": 29000}, {"x": "2023 (est.)", "y": 29529}]


def test_title_and_subtitle():
    panel = fc.build_panel(mk_record(), 2023, TREND)
    assert panel["title"] == "Burton Demographics"
    assert "ACS 2023" in panel["subtitle"]


def test_headline_stats():
    stats = {s["label"]: s["value"] for s in fc.build_panel(mk_record(), 2023, TREND)["stats"]}
    assert stats["Population"] == "29,529"
    assert stats["Median age"] == "42.5"
    assert stats["Median household income"] == "$57,767"
    assert stats["Owner-occupied homes"] == "75%"


def test_derived_rates():
    stats = {s["label"]: s["value"] for s in fc.build_panel(mk_record(), 2023, TREND)["stats"]}
    assert stats["Bachelor's degree or higher"] == "18%"   # (100+50+20+10)/1000
    assert stats["Unemployment rate"] == "8%"              # 80/1000 civilian labor force
    assert stats["Below poverty line"] == "15%"            # 150/1000
    assert stats["Veterans"] == "12%"                      # 120/1000


def test_charts_present_with_trend():
    charts = fc.build_panel(mk_record(), 2023, TREND)["charts"]
    titles = [c["title"] for c in charts]
    assert "Population" in titles            # trend chart present
    assert "Age distribution" in titles
    assert "Educational attainment (age 25+)" in titles
    assert "How residents get to work" in titles
    assert len(charts) == 6


def test_trend_omitted_when_insufficient_points():
    panel = fc.build_panel(mk_record(), 2023, [])
    titles = [c["title"] for c in panel["charts"]]
    assert "Population" not in titles
    assert len(panel["charts"]) == 5
    assert "Decennial" not in panel["source"]


def test_commute_partition_labels():
    charts = {c["title"]: c for c in fc.build_panel(mk_record(), 2023, TREND)["charts"]}
    commute = charts["How residents get to work"]["series"]
    labels = [s["label"] for s in commute]
    assert labels == ["Drove alone", "Carpooled", "Public transit",
                      "Walked / bicycled", "Worked from home", "Other"]


def test_age_bands():
    charts = {c["title"]: c for c in fc.build_panel(mk_record(), 2023, TREND)["charts"]}
    bands = [s["label"] for s in charts["Age distribution"]["series"]]
    assert bands == ["Under 18", "18-34", "35-54", "55-64", "65+"]
    # 18-34 band sums 12 member codes (6 male + 6 female) x 10 each = 120
    band_18_34 = next(s for s in charts["Age distribution"]["series"] if s["label"] == "18-34")
    assert band_18_34["value"] == 120


def test_tos_notice_present():
    notes = fc.build_panel(mk_record(), 2023, TREND)["notes"]
    assert any("not endorsed or certified by the Census Bureau" in n for n in notes)


def test_grouped_vars_helper_dedupes_and_suffixes():
    out = fc._grouped_vars("B15003", fc.EDU_GROUPS)
    assert "B15003_002E" in out and "B15003_025E" in out
    assert len(out) == len(set(out))  # no duplicates
