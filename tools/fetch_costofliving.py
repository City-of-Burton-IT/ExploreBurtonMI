# Build public/info-costofliving.json for the "What it costs to live here" dashboard.
#
# Sources (all public, redistributable):
#   * US Census ACS 5-year: housing costs and income for Burton city (place
#     26-12060), the Flint MSA (22420), Michigan and the United States. A free
#     Census API key is required (env CENSUS_API_KEY or --key); never committed.
#   * BEA Regional Price Parities (RPP, US = 100) for the Flint MSA and Michigan,
#     read from the FRED mirrors of the BEA tables (keyless text endpoint). If
#     FRED is unreachable, pass --rpp-file with the same series as JSON
#     ({"RPPALL22420": {"2024": 93.034, ...}, ...}) copied from BEA/FRED by hand.
#   * Optional City records: residential aggregates (median arm's-length sale
#     price by year, principal residence exemption share) exported from the
#     City's BS&A Assessing database by tools/Export-BsaCostOfLiving.ps1 into
#     tools/data/bsa-residential.json. Aggregates only, never parcel rows.
#
# Framing (issue #23): this is an honest "what it costs to live here" view, not an
# "affordable" pitch. Every cost stat carries its margin of error and sits next to
# the income and rent-burden figures that cut the other way. RPP is metro-level
# only; there is no place-level price index, and the panel says so.
#
# Re-runnable annually (committed output; the site reads the JSON, never the API):
#   CENSUS_API_KEY=... python tools/fetch_costofliving.py [--year 2024] [--rpp-year 2024]
from __future__ import annotations

import argparse
import json
import os
import sys

from lib.httpio import get_bytes, get_json
from lib.iox import write_json
from lib.paths import public_path

STATE_FIPS = "26"        # Michigan
PLACE_FIPS = "12060"     # Burton city (GEOID 2612060)
MSA_CODE = "22420"       # Flint, MI Metro Area (Genesee County)
OUT = public_path("info-costofliving.json")
CITY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-residential.json")

# ACS variables: estimate (E) and 90% margin of error (M).
ACS_VARS = [
    "NAME",
    "B19013_001E", "B19013_001M",   # median household income
    "B25064_001E", "B25064_001M",   # median gross rent
    "B25077_001E", "B25077_001M",   # median home value (owner-occupied)
    "B25088_002E", "B25088_002M",   # median selected monthly owner costs, with a mortgage
    "B25070_001E",                  # renter households (gross rent as % of income: total)
    "B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E",  # 30-34.9, 35-39.9, 40-49.9, 50%+
    "B25070_011E",                  # not computed
]

# Geography label -> ACS "for"/"in" clauses.
GEOS = [
    ("Burton", f"for=place:{PLACE_FIPS}&in=state:{STATE_FIPS}"),
    ("Flint metro", f"for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:{MSA_CODE}"),
    ("Michigan", f"for=state:{STATE_FIPS}"),
    ("United States", "for=us:1"),
]

# FRED mirrors of BEA RPP tables. (series id, area, component label)
RPP_SERIES = [
    ("RPPALL22420", "Flint metro", "All items"),
    ("RPPGOOD22420", "Flint metro", "Goods"),
    ("RPPSERVERENT22420", "Flint metro", "Housing"),
    ("RPPSERVEOTH22420", "Flint metro", "Other services"),
    ("MIRPPALL", "Michigan", "All items"),
    ("MIRPPGOOD", "Michigan", "Goods"),
    ("MIRPPSERVERENT", "Michigan", "Housing"),
    ("MIRPPSERVEOTH", "Michigan", "Other services"),
]
FRED_TXT = "https://fred.stlouisfed.org/data/{sid}.txt"
BEA_RPP_PAGE = "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def fetch_acs(year: int, key: str) -> dict[str, dict[str, str]]:
    """Return {geo label: {variable: value}} for every geography in GEOS."""
    out: dict[str, dict[str, str]] = {}
    for label, clause in GEOS:
        url = (f"https://api.census.gov/data/{year}/acs/acs5"
               f"?get={','.join(ACS_VARS)}&{clause}&key={key}")
        rows = get_json(url, timeout=40)
        out[label] = dict(zip(rows[0], rows[1]))
    if "burton" not in out["Burton"].get("NAME", "").lower():
        sys.exit(f"Unexpected place NAME: {out['Burton'].get('NAME')!r} (check FIPS codes)")
    return out


def parse_fred_txt(text: str) -> dict[str, float]:
    """Parse a FRED .txt series into {year: value}; header lines are skipped."""
    series: dict[str, float] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or len(parts[0]) != 10 or parts[0][4] != "-":
            continue
        try:
            series[parts[0][:4]] = float(parts[1])
        except ValueError:
            continue  # "." marks a missing observation on FRED
    return series


def fetch_rpp() -> dict[str, dict[str, float]]:
    """Return {series id: {year: value}} from the FRED text mirrors."""
    out = {}
    for sid, *_ in RPP_SERIES:
        text = get_bytes(FRED_TXT.format(sid=sid), timeout=40).decode("utf-8", "replace")
        series = parse_fred_txt(text)
        if not series:
            raise RuntimeError(f"FRED series {sid} parsed to no observations")
        out[sid] = series
    return out


def load_city_file(path: str) -> dict:
    """Read and validate the BS&A aggregate export written by
    tools/Export-BsaCostOfLiving.ps1. Aggregates only; a missing or implausible
    figure is rejected rather than published."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_city(raw, path)


def validate_city(raw: object, where: str = "city file") -> dict:
    if not isinstance(raw, dict):
        sys.exit(f"{where}: expected an object")
    res = raw.get("residential")
    if not isinstance(res, dict):
        sys.exit(f"{where}: missing 'residential' object")
    for key in ("parcels", "median_sev", "median_taxable", "pre_parcels"):
        if not isinstance(res.get(key), int) or res[key] <= 0:
            sys.exit(f"{where}: residential.{key} must be a positive integer")
    if res["pre_parcels"] > res["parcels"]:
        sys.exit(f"{where}: pre_parcels exceeds parcels")
    sales = raw.get("sales")
    if not isinstance(sales, list) or not sales:
        sys.exit(f"{where}: 'sales' must be a non-empty list")
    years = []
    for row in sales:
        if not isinstance(row, dict):
            sys.exit(f"{where}: each sales row must be an object")
        for key in ("year", "sales", "median_price"):
            if not isinstance(row.get(key), int) or row[key] <= 0:
                sys.exit(f"{where}: sales.{key} must be a positive integer")
        years.append(row["year"])
    if years != sorted(set(years)):
        sys.exit(f"{where}: sales years must be ascending and unique")
    for key in ("extracted", "assessment_year", "_source"):
        if key not in raw:
            sys.exit(f"{where}: missing '{key}'")
    return raw


def rent_burden_share(row: dict[str, str]) -> tuple[float, int, int]:
    """(percent of renters paying 30%+ of income, numerator, denominator).

    The denominator excludes B25070_011 ("not computed", e.g. no cash rent),
    matching how the Census tabulates the share."""
    burdened = sum(_int(row[f"B25070_{c}E"]) for c in ("007", "008", "009", "010"))
    computed = _int(row["B25070_001E"]) - _int(row["B25070_011E"])
    share = round(100 * burdened / computed, 1) if computed else 0.0
    return share, burdened, computed


def _money(v: int) -> str:
    return f"${v:,}"


def _rpp_value(rpp: dict, sid: str, year: int) -> float:
    try:
        return rpp[sid][str(year)]
    except KeyError:
        sys.exit(f"RPP series {sid} has no {year} observation (years: {sorted(rpp.get(sid, {}))})")


def build_panel(acs: dict[str, dict[str, str]], rpp: dict[str, dict[str, float]],
                year: int, rpp_year: int, city: dict | None = None) -> dict:
    b = acs["Burton"]
    geos = ["Burton", "Flint metro", "Michigan", "United States"]

    def est(var: str, geo: str) -> int:
        return _int(acs[geo][var])

    def bench(var: str, fmt) -> list[dict]:
        return [{"name": g, "value": fmt(est(var, g))} for g in geos if g != "Burton"]

    def moe_hint(var: str, per: str = "") -> str:
        return f"Margin of error ±{_money(_int(b[var]))}{per} (90% confidence)"

    burden = {g: rent_burden_share(acs[g]) for g in geos}
    rpp_all = _rpp_value(rpp, "RPPALL22420", rpp_year)
    rpp_mi_all = _rpp_value(rpp, "MIRPPALL", rpp_year)

    stats = [
        {"label": "Median home value", "value": _money(est("B25077_001E", "Burton")),
         "hint": moe_hint("B25077_001M"), "benchmarks": bench("B25077_001E", _money)},
        {"label": "Median gross rent", "value": f"{_money(est('B25064_001E', 'Burton'))}/mo",
         "hint": moe_hint("B25064_001M", "/mo"),
         "benchmarks": bench("B25064_001E", lambda v: f"{_money(v)}/mo")},
        {"label": "Owner costs with a mortgage", "value": f"{_money(est('B25088_002E', 'Burton'))}/mo",
         "hint": moe_hint("B25088_002M", "/mo"),
         "benchmarks": bench("B25088_002E", lambda v: f"{_money(v)}/mo")},
        {"label": "Median household income", "value": _money(est("B19013_001E", "Burton")),
         "hint": moe_hint("B19013_001M"), "benchmarks": bench("B19013_001E", _money)},
        {"label": "Renters spending 30% or more on rent", "value": f"{burden['Burton'][0]}%",
         "hint": f"{burden['Burton'][1]:,} of {burden['Burton'][2]:,} renter households",
         "benchmarks": [{"name": g, "value": f"{burden[g][0]}%"} for g in geos if g != "Burton"]},
        {"label": "Flint metro price level", "value": f"{rpp_all:.1f}",
         "hint": f"US = 100; BEA {rpp_year}, all items. Metro-wide, not Burton-specific.",
         "benchmarks": [{"name": "Michigan", "value": f"{rpp_mi_all:.1f}"},
                        {"name": "United States", "value": "100"}]},
    ]

    compare_rows = [
        {"label": "Median home value", "unit": "$",
         "values": [{"name": g, "value": est("B25077_001E", g)} for g in geos]},
        {"label": "Median gross rent (monthly)", "unit": "$",
         "values": [{"name": g, "value": est("B25064_001E", g)} for g in geos]},
        {"label": "Owner costs with a mortgage (monthly)", "unit": "$",
         "values": [{"name": g, "value": est("B25088_002E", g)} for g in geos]},
        {"label": "Median household income", "unit": "$",
         "values": [{"name": g, "value": est("B19013_001E", g)} for g in geos]},
        {"label": "Renters spending 30% or more on rent", "unit": "%",
         "values": [{"name": g, "value": burden[g][0]} for g in geos]},
    ]

    components = [("All items", "RPPALL"), ("Goods", "RPPGOOD"),
                  ("Housing", "RPPSERVERENT"), ("Other services", "RPPSERVEOTH")]
    # An index with US = 100 is a comparison, not parts of a whole, so it is a
    # compare chart (one row per category) rather than bars.
    price_rows = [
        {"label": lab, "unit": "",
         "values": [{"name": "Flint metro", "value": _rpp_value(rpp, f"{sid}{MSA_CODE}", rpp_year)},
                    {"name": "Michigan", "value": _rpp_value(rpp, f"MI{sid}", rpp_year)},
                    {"name": "United States", "value": 100}]}
        for lab, sid in components
    ]
    years = sorted(y for y in rpp["RPPALL22420"] if int(y) >= rpp_year - 4)
    lines = [
        {"label": "Flint metro, all items",
         "points": [{"x": y, "y": rpp["RPPALL22420"][y]} for y in years if y in rpp["RPPALL22420"]]},
        {"label": "Flint metro, housing",
         "points": [{"x": y, "y": rpp["RPPSERVERENT22420"][y]} for y in years if y in rpp["RPPSERVERENT22420"]]},
        {"label": "Michigan, all items",
         "points": [{"x": y, "y": rpp["MIRPPALL"][y]} for y in years if y in rpp["MIRPPALL"]]},
    ]

    charts = [
        {"type": "compare", "title": "How Burton compares: housing costs and income", "rows": compare_rows},
        {"type": "compare", "title": "Flint metro price level by category (US = 100)", "rows": price_rows},
        {"type": "trend", "title": "Flint metro price level over time (US = 100)", "unit": "", "lines": lines},
    ]

    explainer_items = [
        {"term": "Price level (RPP)",
         "body": "The Bureau of Economic Analysis compares what goods, rents and services cost in each "
                 "metro area with the national average, set to 100. A value of 93 means prices run about "
                 "7% below the national average. It exists only for metro areas and states, so the figure "
                 "shown is for the whole Flint metro (Genesee County), not Burton alone."},
        {"term": "Cost-burdened renters",
         "body": "Households paying 30% or more of their income in gross rent (rent plus utilities). "
                 "The Census treats that line as the point where housing starts to crowd out other needs."},
        {"term": "Why income is on a cost dashboard",
         "body": "Burton's rents and home values are far below the national median, but so is household "
                 "income. Comparing costs without income would make the city look cheaper to live in than "
                 "it is for the people who already live here."},
        {"term": "Margins of error",
         "body": "ACS figures are survey estimates averaged over five years. Each Burton figure shows its "
                 "90% margin of error; the gaps to Michigan and the nation are far larger than those margins, "
                 "while the gap to the Flint metro usually is not."},
    ]

    source = (f"US Census Bureau, American Community Survey (ACS) {year} 5-year estimates ({year - 4}-{year}) for "
              f"Burton city, the Flint, MI metro area, Michigan and the United States; US Bureau of Economic "
              f"Analysis, Regional Price Parities {rpp_year} (via FRED).")
    notes = [
        "Dollar figures are nominal (not inflation-adjusted) ACS five-year averages, not exact counts. "
        "Rent-burden shares exclude renter households whose burden the Census could not compute.",
        "Regional Price Parities are metro-level and revise from year to year; the Flint metro series "
        "moved several points between recent years, so treat small differences as noise.",
        "This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.",
    ]

    if city:
        res = city["residential"]
        latest = city["sales"][-1]
        pre_share = round(100 * res["pre_parcels"] / res["parcels"], 1)
        stats.append({
            "label": "Typical home sale price",
            "value": _money(latest["median_price"]),
            "hint": f"Median of {latest['sales']:,} arm's-length sales in {latest['year']}, City assessing records",
            "benchmarks": [{"name": f"Census estimate, ACS {year}", "value": _money(est("B25077_001E", "Burton"))}],
        })
        stats.append({
            "label": "Homes with a principal residence exemption",
            "value": f"{pre_share}%",
            "hint": f"{res['pre_parcels']:,} of {res['parcels']:,} residential parcels on the {city['assessment_year']} roll",
        })
        charts.append({
            "type": "trend", "title": "What Burton homes sold for", "unit": "$",
            "points": [{"x": str(row["year"]), "y": row["median_price"]} for row in city["sales"]],
        })
        explainer_items.append({
            "term": "City records next to Census estimates",
            "body": "The Census home value is what owners say their home is worth, averaged over five years. The "
                    "sale price comes from the City's own assessing records: the median of arm's-length sales "
                    "(a willing buyer and seller, no family or foreclosure transfers) in each calendar year. "
                    "Recent sales running above the Census figure is normal; the two measure different things.",
        })
        explainer_items.append({
            "term": "Principal residence exemption",
            "body": "Michigan homeowners who live in their home as their main residence are exempt from the "
                    "school operating levy. The share of residential parcels with that exemption is the City's "
                    "own measure of owner-occupancy.",
        })
        source += (f" City of Burton assessing records, {city['assessment_year']} roll and sales through "
                   f"{latest['year']} (aggregates extracted {city['extracted']}).")
        notes.append(
            "City sale figures are medians of arm's-length residential sales over $10,000 recorded by the "
            "City Assessor; they are not adjusted for inflation and exclude family transfers, foreclosures "
            "and other non-market sales. Only aggregates are published, never individual parcels."
        )

    return {
        "title": "What it costs to live here",
        "subtitle": f"Housing costs, income, and prices: Census ACS {year} five-year and BEA {rpp_year}",
        "stats": stats,
        "charts": charts,
        "explainer": {
            "title": "How to read these numbers",
            "intro": "Costs only mean something next to what people earn. This dashboard shows both.",
            "items": explainer_items,
        },
        "source": source,
        "links": [
            {"text": "Census QuickFacts: Burton", "href": "https://www.census.gov/quickfacts/burtoncitymichigan"},
            {"text": "BEA Regional Price Parities", "href": BEA_RPP_PAGE},
        ],
        "notes": notes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=2024, help="ACS 5-year end year")
    ap.add_argument("--rpp-year", type=int, default=2024, help="BEA RPP data year")
    ap.add_argument("--key", default=os.environ.get("CENSUS_API_KEY"))
    ap.add_argument("--rpp-file", help="JSON {series id: {year: value}} used instead of fetching FRED")
    ap.add_argument("--city-file", default=CITY_FILE if os.path.exists(CITY_FILE) else None,
                    help="BS&A aggregate export from tools/Export-BsaCostOfLiving.ps1 "
                         "(default: tools/data/bsa-residential.json when present; pass '' to skip)")
    args = ap.parse_args()
    if not args.key:
        sys.exit("Census API key required: set CENSUS_API_KEY or pass --key. "
                 "Free signup: https://api.census.gov/data/key_signup.html")

    acs = fetch_acs(args.year, args.key)
    if args.rpp_file:
        with open(args.rpp_file, encoding="utf-8") as fh:
            rpp = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
        print(f"  RPP from {args.rpp_file}")
    else:
        rpp = fetch_rpp()

    city = load_city_file(args.city_file) if args.city_file else None
    if city:
        print(f"  City records from {args.city_file} (extracted {city['extracted']})")

    panel = build_panel(acs, rpp, args.year, args.rpp_year, city)
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    for s in panel["stats"]:
        bench = ", ".join(b["name"] + " " + b["value"] for b in s.get("benchmarks", []))
        print(f"  {s['label']}: {s['value']}" + (f"  ({bench})" if bench else ""))


if __name__ == "__main__":
    main()
