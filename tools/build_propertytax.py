"""Build public/info-propertytax.json: the Property Taxes dashboard.

Answers the question residents actually ask: "when I pay my property tax bill,
where does the money go?" It presents a provisional City rate while the
current L-4029 is pending and keeps the separately dated complete-bill estimate
distinct so residents are not shown arithmetic that mixes source periods.

Figures are held as documented constants from authoritative public sources and
refreshed yearly:
  * City + overlapping per-authority rates: City of Burton audited financial
    statements (ACFR), Statistical Section: "Direct and Overlapping Property
    Tax Rates, Last Ten Fiscal Years" (source: Genesee County Apportionment).
  * Total rate by school district: Michigan Dept. of Treasury, "2025 Total
    Property Tax Rates in Michigan" (L-4029 totals), City of Burton block.

Mills = dollars per $1,000 of TAXABLE value (taxable value is usually about half
of a home's market value). The per-authority breakdown shown is for a typical
HOMESTEAD (owner-occupied) home; non-homestead pays about 18 mills more, almost
all to schools. The exact school portion varies by which of Burton's 7 school
districts a home is in, the "Schools & State Education" slice is the remainder
for a representative district so the breakdown sums to a real total bill.

Re-runnable (committed output; the site reads the JSON):
    python tools/build_propertytax.py

Uses the shared tools/lib helpers (repo paths, atomic writes).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from lib.iox import write_json
from lib.paths import public_path

OUT = public_path("info-propertytax.json")

# --- City rate from the certified tax roll (BS&A Tax module) --------------------
# Decision 2026-10-06: City records are the source of truth. tools/Export-BsaTaxRoll.ps1
# writes tools/data/bsa-taxroll.json with the City millage lines as billed on the
# roll (tax unit classification 7, DDA excluded), the levy by taxing unit, the
# median City tax on a homestead residential parcel, and taxable value.
TAXROLL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-taxroll.json")
FULL_BILL_RATE_PERIOD = "2025 published rates"
# The latest complete published district totals are still 2025; their City
# component (13.44) is used only for the 2025 authority chart.
PUBLISHED_2025_CITY_TOTAL = 13.44

# Which roll line codes make up each City service levy.
CITY_LINE_GROUPS = [
    ("general-operating", "General city operations", "City Charter", ("UNIT OP",), False),
    ("police", "Police services", "Voter approved", ("POLICE OP", "POLICE"), True),
    ("fire", "Fire services", "Voter approved", ("FIRE",), True),
]

# Taxing-unit classification codes on the roll -> public label (order = chart order).
UNIT_GROUPS = [
    (7, "City of Burton"),
    (6, "Genesee County"),
    (2, "Local school district operating"),
    (3, "Local school district debt"),
    (5, "Local school district sinking fund"),
    (1, "State Education Tax"),
    (9, "Genesee ISD"),
    (8, "Mott Community College"),
]


def load_taxroll(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_taxroll(raw, path)


def validate_taxroll(raw: Any, where: str = "tax-roll file") -> dict:
    if not isinstance(raw, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "tax_year", "city_mills", "city_lines", "levy_by_unit", "homestead"):
        if key not in raw:
            sys.exit(f"{where}: missing '{key}'")
    if not isinstance(raw["city_mills"], (int, float)) or not 5 <= raw["city_mills"] <= 25:
        sys.exit(f"{where}: city_mills {raw['city_mills']!r} is outside the plausible 5-25 range")
    lines = raw["city_lines"]
    if not isinstance(lines, list) or len(lines) < 2:
        sys.exit(f"{where}: city_lines must list at least two levies")
    for ln in lines:
        if not isinstance(ln.get("code"), str) or not isinstance(ln.get("mills"), (int, float)) or ln["mills"] <= 0:
            sys.exit(f"{where}: city_lines entries need a code and positive mills")
    if abs(sum(ln["mills"] for ln in lines) - raw["city_mills"]) > 0.0005:
        sys.exit(f"{where}: city_lines do not add up to city_mills")
    known = {code for _, _, _, codes, _ in CITY_LINE_GROUPS for code in codes}
    unknown = [ln["code"] for ln in lines if ln["code"] not in known]
    if unknown:
        sys.exit(f"{where}: unmapped City levy codes {unknown}; add them to CITY_LINE_GROUPS")
    for u in raw["levy_by_unit"]:
        if not isinstance(u.get("levy"), int) or u["levy"] < 0 or not isinstance(u.get("classification"), int):
            sys.exit(f"{where}: levy_by_unit entries need integer levy and classification")
    hs = raw["homestead"]
    if not isinstance(hs.get("parcels"), int) or hs["parcels"] < 1000 or not isinstance(hs.get("median_city_tax"), (int, float)):
        sys.exit(f"{where}: homestead block implausible")
    return raw


def build_city_levies(taxroll: dict) -> list:
    by_code = {ln["code"]: ln for ln in taxroll["city_lines"]}
    year = taxroll["tax_year"]
    levies = []
    for lid, service, auth, codes, voter in CITY_LINE_GROUPS:
        mills = round(sum(by_code[c]["mills"] for c in codes if c in by_code), 4)
        if mills <= 0:
            continue
        levies.append({
            "id": lid,
            "service": service,
            "authorization": auth,
            "description": f"{year} tax roll line{'s' if len(codes) > 1 else ''} {', '.join(codes)} as billed.",
            "mills": mills,
            "voterApproved": voter,
        })
    return levies


def build_levy_chart(taxroll: dict) -> dict:
    totals: dict[int, int] = {}
    for u in taxroll["levy_by_unit"]:
        totals[u["classification"]] = totals.get(u["classification"], 0) + u["levy"]
    series = []
    for cls, label in UNIT_GROUPS:
        amount = totals.pop(cls, 0)
        if amount > 0:
            series.append({"label": label, "value": round(amount / 1e6, 2)})
    other = sum(totals.values())
    if other > 0:
        series.append({"label": "Other authorities", "value": round(other / 1e6, 2)})
    return {"type": "bars", "title": f"{taxroll['tax_year']} property tax levy by taxing unit ($M)",
            "unit": "$M", "series": series}

# --- Overlapping authorities, homestead, uniform across Burton (ACFR p.118) ------
COUNTY = 17.46       # Genesee County (operating, parks, library, health, paramedics, ...)
MOTT = 2.54          # Mott Community College
ISD = 3.68           # Genesee Intermediate School District
MTA = 1.21           # Mass Transportation Authority
AIRPORT = 0.47       # Bishop International Airport

# Representative typical homestead total (ACFR latest "Total Homestead").
HOMESTEAD_TOTAL = 45.99

# --- Total tax rate by school district, homestead (MI Treasury 2025 Total Rates) -
# (district, homestead total, non-homestead total) mills, MI Treasury 2025.
DISTRICT_RATES = [
    ("Atherton", 41.86, 59.72),
    ("Carman-Ainsworth", 43.12, 61.12),
    ("Kearsley", 44.23, 62.23),
    ("Bentley", 44.36, 61.84),
    ("Davison", 44.37, 62.14),
    ("Grand Blanc", 45.78, 63.78),
    ("Bendle", 53.47, 71.47),
]
DISTRICT_HOMESTEAD = [(name, hs) for name, hs, _ in DISTRICT_RATES]

# --- City total direct millage, last 10 fiscal years (ACFR p.118) ----------------
CITY_MILLAGE_HISTORY = [
    ("2017", 14.20), ("2018", 13.49), ("2019", 13.49), ("2020", 13.48),
    ("2021", 13.48), ("2022", 13.44), ("2023", 13.44), ("2024", 13.44),
    ("2025", 13.44), ("2026", 13.44),
]

EXAMPLE_TAXABLE = 50_000  # a ~$100k market-value homesteaded home


def build_estimator(taxroll: dict) -> dict:
    return {
        "cityRatePeriod": f"{taxroll['tax_year']} tax roll, certified levy",
        "fullBillRatePeriod": FULL_BILL_RATE_PERIOD,
        "cityMills": round(float(taxroll["city_mills"]), 4),
        "cityLevies": build_city_levies(taxroll),
        "districts": [
            {"name": name, "homestead": hs, "nonHomestead": nhs}
            for name, hs, nhs in DISTRICT_RATES
        ],
    }


def main() -> int:
    taxroll = load_taxroll(TAXROLL_FILE)
    year = taxroll["tax_year"]
    city_total = round(float(taxroll["city_mills"]), 4)
    levies = build_city_levies(taxroll)
    by_id = {lv["id"]: lv["mills"] for lv in levies}
    uniform = PUBLISHED_2025_CITY_TOTAL + COUNTY + MOTT + ISD + MTA + AIRPORT
    schools_set = round(HOMESTEAD_TOTAL - uniform, 2)  # remainder = schools + State Ed

    city_dollars = city_total * EXAMPLE_TAXABLE / 1000
    lo_total = round(DISTRICT_HOMESTEAD[0][1] * EXAMPLE_TAXABLE / 1000)
    hi_total = round(DISTRICT_HOMESTEAD[-1][1] * EXAMPLE_TAXABLE / 1000)

    stats = [
        {
            "label": "City of Burton's rate",
            "value": f"{city_total:.2f} mills",
            "hint": f"{year} tax roll as billed, City Treasurer (BS&A)",
        },
        {
            "label": "Rate status",
            "value": "Certified",
            "hint": f"{year} levy as billed on the tax roll",
        },
        {
            "label": "City tax on a $50k-taxable home",
            "value": f"${round(city_dollars):,}/yr",
            "hint": f"{city_total:.4f} mills on $50,000 taxable; about a $100,000 market-value home",
        },
        {
            "label": "School districts in Burton",
            "value": "7",
            "hint": "2025 complete-bill rates vary by district",
        },
        {
            "label": "Median City tax, homestead home",
            "value": f"${round(taxroll['homestead']['median_city_tax']):,}/yr",
            "hint": (f"{taxroll['homestead']['parcels']:,} owner-occupied homes with a full principal residence "
                     f"exemption, {year} roll"),
        },
    ]

    breakdown = [
        ("Genesee County", COUNTY, "#c0392b"),
        ("City of Burton", PUBLISHED_2025_CITY_TOTAL, "#2c57a0"),
        ("Schools & State Education", schools_set, "#e08a00"),
        ("Genesee ISD", ISD, "#7e57c2"),
        ("Mott Community College", MOTT, "#00897b"),
        ("Public transit (MTA)", MTA, "#5c6bc0"),
        ("Bishop Airport", AIRPORT, "#8d6e63"),
    ]

    charts = [
        {"type": "bars", "title": "Where a typical 2025 homestead tax bill went (mills)", "unit": "",
         "series": [{"label": lbl, "value": v, "color": c} for lbl, v, c in breakdown]},
        {"type": "bars", "title": "Total homestead tax rate by school district (mills)", "unit": "",
         "series": [{"label": lbl, "value": v} for lbl, v in DISTRICT_HOMESTEAD]},
        {"type": "trend", "title": "Reported City millage, FY2017-FY2026", "unit": "",
         "points": [{"x": yr, "y": v} for yr, v in CITY_MILLAGE_HISTORY]},
        build_levy_chart(taxroll),
    ]

    summary = {
        "heading": "What this means for you",
        "body": [
            (
                f"Burton's City rate on the {year} tax roll is {city_total:.4f} mills, read directly "
                "from the City's billing records: general operations "
                f"{by_id.get('general-operating', 0):.4f}, Police {by_id.get('police', 0):.4f}, "
                f"and Fire {by_id.get('fire', 0):.4f} mills."
            ),
            (
                f"At ${EXAMPLE_TAXABLE:,} of taxable value, the City portion is about "
                f"${round(city_dollars):,} a year. The latest complete published bill rates "
                f"are from 2025 and range from about ${lo_total:,} to ${hi_total:,} at that "
                "taxable value, depending on school district."
            ),
            (
                f"The median City tax on an owner-occupied home was "
                f"${round(taxroll['homestead']['median_city_tax']):,} on the {year} roll, across "
                f"{taxroll['homestead']['parcels']:,} homes with a full principal residence exemption."
            ),
            (
                "County, schools, the State, ISD, college, transit, airport, and other "
                "authorities receive their own portions; those amounts do not become City revenue."
            ),
        ],
    }

    estimator = build_estimator(taxroll)

    panel = {
        "title": "Property Taxes",
        "subtitle": "Where your property tax bill actually goes",
        "summary": summary,
        "estimator": estimator,
        "stats": stats,
        "charts": charts,
        "source": (
            f"City of Burton tax roll {year} (BS&A Tax module, aggregates extracted {taxroll['extracted']}) "
            "for the City rate, levy by taxing unit and homestead median; City of Burton audited financial "
            "statements for the FY2017-FY2026 reported millage; Michigan Department of Treasury, 2025 Total "
            "Property Tax Rates in Michigan, for complete-bill district rates."
        ),
        "links": [
            {
                "text": "City of Burton 2026-27 Approved Budget",
                "href": "https://www.burtonmi.gov/government/controller_s_office/budgets.php",
            },
            {
                "text": "Genesee County L-4029 information",
                "href": "https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php",
            },
            {
                "text": "Michigan property-tax estimator",
                "href": "https://www.michigan.gov/taxes/property/estimator",
            },
            {"text": "City Finances dashboard", "href": "#finances"},
        ],
        "notes": [
            (
                "One mill is $1 per $1,000 of taxable value. Taxable value is shown on the "
                "assessment notice and is not the same as market value."
            ),
            (
                f"The City rate and levy chart come from the {year} tax roll as billed (summer levy; "
                "winter lines are added once billed). The complete-bill district estimate and the 2025 "
                "authority chart use 2025 published rates and are dated separately."
            ),
            (
                "Estimate only. Actual bills can differ because of exact parcel values, exemptions, "
                "special assessments, administrative fees, and a possible Downtown Development "
                "Authority levy for affected parcels. Not a tax statement."
            ),
        ],
    }

    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  City {city_total:.4f} mills on the {year} roll; homestead median City tax "
          f"${round(taxroll['homestead']['median_city_tax']):,}")
    print(f"  2025 complete-bill districts: {len(DISTRICT_RATES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
