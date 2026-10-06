"""Unit tests for the cost-of-living panel builder (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fetch_costofliving as col  # noqa: E402


def _acs_row(name, income, rent, value, owner, renters, b30, b35, b40, b50, nc):
    return {
        "NAME": name,
        "B19013_001E": str(income), "B19013_001M": "100",
        "B25064_001E": str(rent), "B25064_001M": "10",
        "B25077_001E": str(value), "B25077_001M": "1000",
        "B25088_002E": str(owner), "B25088_002M": "20",
        "B25070_001E": str(renters),
        "B25070_007E": str(b30), "B25070_008E": str(b35),
        "B25070_009E": str(b40), "B25070_010E": str(b50),
        "B25070_011E": str(nc),
    }


ACS = {
    "Burton": _acs_row("Burton city, Michigan", 60052, 1009, 141600, 1268, 2965, 101, 74, 346, 782, 200),
    "Flint metro": _acs_row("Flint, MI Metro Area", 62281, 989, 182400, 1455, 48971, 3729, 3243, 4069, 12695, 2000),
    "Michigan": _acs_row("Michigan", 72875, 1129, 231600, 1569, 1092179, 90624, 64494, 86193, 265994, 50000),
    "United States": _acs_row("United States", 80734, 1413, 332700, 1963, 45017354,
                              3872456, 2838920, 3858845, 10852194, 2000000),
}

RPP = {
    "RPPALL22420": {"2022": 90.889, "2023": 89.879, "2024": 93.034},
    "RPPGOOD22420": {"2022": 92.081, "2023": 94.057, "2024": 93.711},
    "RPPSERVERENT22420": {"2022": 68.612, "2023": 65.026, "2024": 74.039},
    "RPPSERVEOTH22420": {"2022": 98.171, "2023": 97.671, "2024": 99.561},
    "MIRPPALL": {"2022": 95.5, "2023": 95.9, "2024": 96.217},
    "MIRPPGOOD": {"2024": 95.993},
    "MIRPPSERVERENT": {"2024": 82.332},
    "MIRPPSERVEOTH": {"2024": 97.0},
}


def test_rent_burden_share_excludes_not_computed_from_denominator():
    share, burdened, computed = col.rent_burden_share(ACS["Burton"])
    assert burdened == 101 + 74 + 346 + 782 == 1303
    assert computed == 2965 - 200 == 2765
    assert share == round(100 * 1303 / 2765, 1) == 47.1


def test_parse_fred_txt_skips_header_and_missing_values():
    text = (
        "Title: Regional Price Parities: All Items for Flint, MI (MSA)\n"
        "Units: Index 2017=100, Not Seasonally Adjusted\n"
        "\n"
        "DATE         VALUE\n"
        "2022-01-01   90.889\n"
        "2023-01-01   .\n"
        "2024-01-01   93.034\n"
    )
    assert col.parse_fred_txt(text) == {"2022": 90.889, "2024": 93.034}


def test_build_panel_shape_and_benchmarks():
    panel = col.build_panel(ACS, RPP, 2024, 2024)

    labels = [s["label"] for s in panel["stats"]]
    assert labels == [
        "Median home value", "Median gross rent", "Owner costs with a mortgage",
        "Median household income", "Renters spending 30% or more on rent", "Flint metro price level",
    ]
    assert len(labels) == len(set(labels))

    home = panel["stats"][0]
    assert home["value"] == "$141,600"
    assert "±$1,000" in home["hint"]
    assert [b["name"] for b in home["benchmarks"]] == ["Flint metro", "Michigan", "United States"]
    assert home["benchmarks"][2]["value"] == "$332,700"

    rent = panel["stats"][1]
    assert rent["value"] == "$1,009/mo"
    assert rent["benchmarks"][0]["value"] == "$989/mo"

    price = panel["stats"][5]
    assert price["value"] == "93.0"
    assert price["benchmarks"] == [{"name": "Michigan", "value": "96.2"}, {"name": "United States", "value": "100"}]

    kinds = [c["type"] for c in panel["charts"]]
    assert kinds == ["compare", "compare", "trend"]
    titles = [c["title"] for c in panel["charts"]]
    assert len(titles) == len(set(titles))

    compare = panel["charts"][0]
    assert [r["label"] for r in compare["rows"]][0] == "Median home value"
    assert compare["rows"][0]["values"][0] == {"name": "Burton", "value": 141600}
    assert compare["rows"][4]["unit"] == "%"

    price = panel["charts"][1]["rows"]
    assert [r["label"] for r in price] == ["All items", "Goods", "Housing", "Other services"]
    assert price[2]["values"] == [
        {"name": "Flint metro", "value": 74.039}, {"name": "Michigan", "value": 82.332},
        {"name": "United States", "value": 100},
    ]

    trend = panel["charts"][2]
    assert [ln["label"] for ln in trend["lines"]] == [
        "Flint metro, all items", "Flint metro, housing", "Michigan, all items",
    ]
    assert trend["lines"][0]["points"] == [
        {"x": "2022", "y": 90.889}, {"x": "2023", "y": 89.879}, {"x": "2024", "y": 93.034},
    ]

    assert "not endorsed or certified by the Census Bureau" in panel["notes"][-1]
    assert panel["explainer"]["items"][0]["term"] == "Price level (RPP)"


def test_build_panel_rejects_missing_rpp_year():
    import pytest

    with pytest.raises(SystemExit):
        col.build_panel(ACS, RPP, 2024, 2019)


CITY = {
    "_source": "test",
    "extracted": "2026-10-06",
    "assessment_year": 2026,
    "residential": {"parcels": 10953, "median_sev": 78300, "median_taxable": 45808, "pre_parcels": 10502},
    "sales": [
        {"year": 2023, "sales": 495, "median_price": 150000},
        {"year": 2024, "sales": 461, "median_price": 155000},
        {"year": 2025, "sales": 466, "median_price": 158000},
    ],
}


def test_city_records_add_sale_price_exemption_and_trend():
    panel = col.build_panel(ACS, RPP, 2024, 2024, CITY)
    labels = [s["label"] for s in panel["stats"]]
    assert labels[-2:] == ["Typical home sale price", "Homes with a principal residence exemption"]
    sale = panel["stats"][-2]
    assert sale["value"] == "$158,000"
    assert "466" in sale["hint"] and "2025" in sale["hint"]
    assert sale["benchmarks"] == [{"name": "Census estimate, ACS 2024", "value": "$141,600"}]
    pre = panel["stats"][-1]
    assert pre["value"] == "95.9%"
    trend = panel["charts"][-1]
    assert trend["type"] == "trend" and trend["title"] == "What Burton homes sold for"
    assert trend["points"] == [
        {"x": "2023", "y": 150000}, {"x": "2024", "y": 155000}, {"x": "2025", "y": 158000},
    ]
    assert "City of Burton assessing records" in panel["source"]
    assert any("Only aggregates are published" in n for n in panel["notes"])
    assert panel["explainer"]["items"][-1]["term"] == "Principal residence exemption"


def test_without_city_records_panel_is_unchanged():
    panel = col.build_panel(ACS, RPP, 2024, 2024)
    assert len(panel["stats"]) == 6 and len(panel["charts"]) == 3
    assert "assessing records" not in panel["source"]


def test_validate_city_rejects_bad_shapes():
    import copy
    import pytest

    bad = copy.deepcopy(CITY)
    bad["residential"]["pre_parcels"] = 99999
    with pytest.raises(SystemExit):
        col.validate_city(bad)
    bad = copy.deepcopy(CITY)
    bad["sales"] = [bad["sales"][1], bad["sales"][0]]
    with pytest.raises(SystemExit):
        col.validate_city(bad)
    bad = copy.deepcopy(CITY)
    del bad["extracted"]
    with pytest.raises(SystemExit):
        col.validate_city(bad)
    assert col.validate_city(copy.deepcopy(CITY)) == CITY
