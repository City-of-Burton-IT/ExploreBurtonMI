# Build public/info-access.json: an Affordability & Access dashboard for the City of
# Burton: cost-of-living burden (housing + transportation), income, car
# dependence, and how many everyday destinations are in town.
#
# Sources (all Genesee County / GCMPC public ArcGIS, org 5ckbIY7K9TUKoseK):
#   - Median_HH_Income_WFL1   (Census tract, Med_HH_Inc)
#   - Cars_per_Household_WFL1  (block group: perc_inc_housing, perc_inc_trans,
#                               autos_per_hh_ami, transit_trips_ami: MODELED for an
#                               Area-Median-Income household, GCMPC LRTP)
#   - LowMod_Income_WFL1       (block group: LOWMOD_PCT, HUD low/moderate income %)
#   - Access_To_Schools_WFL1 / Access_to_Groceries_WFL1 / Access_to_Medical_Facilities_WFL1
#     (amenity POINT locations)
#
# Census areas are kept when their interior point (INTPTLON/LAT) is inside the
# Burton boundary; amenity points are clipped to the boundary. Values are
# aggregated across Burton's census areas (a city-wide summary, not parcel-level).
#
# Re-runnable (committed output; the site reads the JSON, never ArcGIS):
#     python tools/extract_access.py
#
# Uses tools/lib for HTTP + writes.
from __future__ import annotations

import json
import sys

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

BOUNDARY = public_path("boundary.geojson")
OUT_INFO = public_path("info-access.json")

BASE = "https://services2.arcgis.com/5ckbIY7K9TUKoseK/ArcGIS/rest/services"


def _rings() -> list:
    gj = json.load(open(BOUNDARY, encoding="utf-8"))
    geom = gj["geometry"] if gj.get("type") == "Feature" else (
        gj["features"][0]["geometry"] if gj.get("features") else gj)
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [ring for poly in polys for ring in poly]


def _inside(lon: float, lat: float, rings: list) -> bool:
    ins = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                ins = not ins
            j = i
    return ins


def _query(service: str, fields: str, with_geom: bool = False) -> list:
    params = {
        "where": "1=1",
        "outFields": fields,
        "returnGeometry": "true" if with_geom else "false",
        "outSR": "4326",
        "f": "geojson" if with_geom else "json",
        "resultRecordCount": "4000",
    }
    d = get_json(f"{BASE}/{service}/FeatureServer/0/query", params, timeout=120)
    if with_geom:
        return [(f.get("geometry"), f.get("properties", {})) for f in d.get("features", [])]
    return [f["attributes"] for f in d.get("features", [])]


def _burton_areas(rows: list, rings: list) -> list:
    """Keep rows whose census-area interior point is inside Burton."""
    out = []
    for a in rows:
        try:
            lon = float(a.get("INTPTLON20")); lat = float(a.get("INTPTLAT20"))
        except (TypeError, ValueError):
            continue
        if _inside(lon, lat, rings):
            out.append(a)
    return out


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace("%", "").replace(",", "").strip())
    except ValueError:
        return None


def _avg(rows, key):
    vals = [n for n in (_num(a.get(key)) for a in rows) if n is not None and n != 0]
    return sum(vals) / len(vals) if vals else None


def _median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2


def main() -> int:
    rings = _rings()

    inc = _burton_areas(_query("Median_HH_Income_WFL1", "GEOID20,Med_HH_Inc,INTPTLON20,INTPTLAT20"), rings)
    cars = _burton_areas(_query("Cars_per_Household_WFL1",
                                "perc_inc_housing,perc_inc_trans,autos_per_hh_ami,transit_trips_ami,INTPTLON20,INTPTLAT20"), rings)
    if not (inc and cars):
        raise SystemExit("No Burton census areas matched, check the boundary / layers.")

    inc_vals = [v for v in (_num(a.get("Med_HH_Inc")) for a in inc) if v]
    med_income = _median(inc_vals) or 0
    inc_lo, inc_hi = (min(inc_vals), max(inc_vals)) if inc_vals else (0, 0)

    pct_housing = _avg(cars, "perc_inc_housing") or 0
    pct_trans = _avg(cars, "perc_inc_trans") or 0
    ht = pct_housing + pct_trans
    autos = _avg(cars, "autos_per_hh_ami") or 0

    # Income distribution across Burton's neighborhoods (the equity spread).
    bands = [("Under $40k", 0, 40000), ("$40k-$60k", 40000, 60000),
             ("$60k-$80k", 60000, 80000), ("$80k+", 80000, 10**9)]
    band_counts = [(lbl, sum(1 for v in inc_vals if lo <= v < hi)) for lbl, lo, hi in bands]

    stats = [
        {"label": "Typical household income", "value": f"${round(med_income):,}",
         "hint": "median across Burton's neighborhoods"},
        {"label": "Housing + transport cost", "value": f"{round(ht)}% of income",
         "hint": f"housing {round(pct_housing)}% + transport {round(pct_trans)}% (45% = affordable)"},
        {"label": "Cars per household", "value": f"{autos:.1f}",
         "hint": "modeled, typical household"},
        {"label": "Neighborhood income range", "value": f"${round(inc_lo/1000)}k-${round(inc_hi/1000)}k",
         "hint": f"across {len(inc_vals)} census areas (the equity gap)"},
    ]

    charts = [
        {"type": "bars", "title": "Cost of living: share of income (modeled)", "unit": "%",
         "series": [
             {"label": "Housing", "value": round(pct_housing)},
             {"label": "Transportation", "value": round(pct_trans)},
             {"label": "Housing + transport", "value": round(ht)},
         ]},
        {"type": "bars", "title": "Household income across Burton neighborhoods", "unit": "",
         "series": [{"label": lbl, "value": c} for lbl, c in band_counts]},
    ]

    panel = {
        "title": "Affordability & Access",
        "subtitle": "Cost of living, mobility, and household income across Burton",
        "stats": stats,
        "charts": charts,
        "source": ("Genesee County (GCMPC) Long Range Transportation Plan equity layers "
                   "(median income, and modeled housing + transportation cost) for the City of "
                   "Burton."),
        "links": [
            {"text": "Housing + Transportation Affordability Index (CNT)", "href": "https://htaindex.cnt.org/"},
            {"text": "Demographics dashboard", "href": "#demographics"},
        ],
        "notes": [
            "The housing + transportation figures are MODELED estimates for a typical "
            "(area-median-income) household from the regional planning agency (GCMPC), not "
            "billed amounts. The widely used affordability benchmark is 45% of income for "
            "housing + transportation combined; in an auto-dependent suburb, transportation "
            "can cost as much as or more than housing.",
            "Figures are aggregated across Burton's census tracts and block groups (a city-wide "
            "summary), so a specific street or household will differ. Income is the median across "
            "neighborhoods.",
            "Source: Genesee County (GCMPC) equity/access layers; regional planning data, not a "
            "City of Burton statistic.",
        ],
    }
    write_json(OUT_INFO, panel)

    print(f"Wrote {OUT_INFO}")
    print(f"  Burton tracts={len(inc)} bg(cars)={len(cars)}")
    print(f"  median income=${round(med_income):,} range ${round(inc_lo):,}-${round(inc_hi):,}")
    print(f"  H+T: housing {round(pct_housing,1)}% + transport {round(pct_trans,1)}% = {round(ht)}%; autos/hh {autos:.2f}")
    print(f"  income bands: {band_counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
