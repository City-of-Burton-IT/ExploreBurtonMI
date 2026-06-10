"""Build public/info-propertytax.json: the Property Taxes dashboard.

Answers the question residents actually ask: "when I pay my property tax bill,
where does the money go?" The key, often-surprising answer is that most of a
Burton tax bill does NOT go to the City: the City levies about 13.44 mills
(roughly 29% of a typical homestead bill); the largest single piece is Genesee
County, and the rest funds schools, the State Education Tax, the ISD, Mott
Community College, public transit, and the airport.

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

Stdlib only (json), matching the other tools/ scripts.
"""
from __future__ import annotations

import json
import os
import sys

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-propertytax.json"))

# --- City of Burton's own millage (tax year 2025 / FY2026, from the ACFR) --------
CITY_GENERAL = 4.00
CITY_POLICE = 8.44
CITY_FIRE = 0.99
CITY_TOTAL = 13.44   # ACFR "Total direct City taxes" (rounding of the three above)

# --- Overlapping authorities, homestead, uniform across Burton (ACFR p.118) ------
COUNTY = 17.46       # Genesee County (operating, parks, library, health, paramedics, ...)
MOTT = 2.54          # Mott Community College
ISD = 3.68           # Genesee Intermediate School District
MTA = 1.21           # Mass Transportation Authority
AIRPORT = 0.47       # Bishop International Airport

# Representative typical homestead total (ACFR latest "Total Homestead").
HOMESTEAD_TOTAL = 45.99

# --- Total tax rate by school district, homestead (MI Treasury 2025 Total Rates) -
DISTRICT_HOMESTEAD = [
    ("Atherton", 41.86),
    ("Carman-Ainsworth", 43.12),
    ("Kearsley", 44.23),
    ("Bentley", 44.36),
    ("Davison", 44.37),
    ("Grand Blanc", 45.78),
    ("Bendle", 53.47),
]

# --- City total direct millage, last 10 fiscal years (ACFR p.118) ----------------
CITY_MILLAGE_HISTORY = [
    ("2017", 14.20), ("2018", 13.49), ("2019", 13.49), ("2020", 13.48),
    ("2021", 13.48), ("2022", 13.44), ("2023", 13.44), ("2024", 13.44),
    ("2025", 13.44), ("2026", 13.44),
]

EXAMPLE_TAXABLE = 50_000  # a ~$100k market-value homesteaded home


def main() -> int:
    uniform = CITY_TOTAL + COUNTY + MOTT + ISD + MTA + AIRPORT
    schools_set = round(HOMESTEAD_TOTAL - uniform, 2)  # remainder = schools + State Ed
    city_share = round(CITY_TOTAL / HOMESTEAD_TOTAL * 100)

    city_dollars = round(CITY_TOTAL * EXAMPLE_TAXABLE / 1000)
    lo_total = round(DISTRICT_HOMESTEAD[0][1] * EXAMPLE_TAXABLE / 1000)
    hi_total = round(DISTRICT_HOMESTEAD[-1][1] * EXAMPLE_TAXABLE / 1000)

    stats = [
        {"label": "City of Burton's rate", "value": f"{CITY_TOTAL:.2f} mills",
         "hint": f"General {CITY_GENERAL:.2f} + Police {CITY_POLICE:.2f} + Fire {CITY_FIRE:.2f}"},
        {"label": "City's share of your bill", "value": f"~{city_share}%",
         "hint": "the rest goes to county, schools & others"},
        {"label": "City tax on a $50k-taxable home", "value": f"${city_dollars:,}/yr",
         "hint": "about a $100,000 market-value home"},
        {"label": "School districts in Burton", "value": "7",
         "hint": "your total rate depends on which"},
    ]

    breakdown = [
        ("Genesee County", COUNTY, "#c0392b"),
        ("City of Burton", CITY_TOTAL, "#2c57a0"),
        ("Schools & State Education", schools_set, "#e08a00"),
        ("Genesee ISD", ISD, "#7e57c2"),
        ("Mott Community College", MOTT, "#00897b"),
        ("Public transit (MTA)", MTA, "#5c6bc0"),
        ("Bishop Airport", AIRPORT, "#8d6e63"),
    ]

    charts = [
        {"type": "bars", "title": "Where a typical homestead tax bill goes (mills)", "unit": "",
         "series": [{"label": lbl, "value": v, "color": c} for lbl, v, c in breakdown]},
        {"type": "bars", "title": "Total homestead tax rate by school district (mills)", "unit": "",
         "series": [{"label": lbl, "value": v} for lbl, v in DISTRICT_HOMESTEAD]},
        {"type": "trend", "title": "City of Burton's own millage, last 10 years", "unit": "",
         "points": [{"x": yr, "y": v} for yr, v in CITY_MILLAGE_HISTORY]},
    ]

    summary = {
        "heading": "What this means for you",
        "body": [
            f"When you pay your property tax bill, most of it does not go to the City of Burton. "
            f"The City levies {CITY_TOTAL:.2f} mills, about {city_share}% of a typical owner-occupied "
            "(homestead) bill. The single largest piece is Genesee County; the rest funds your school "
            "district, the State Education Tax, the Genesee ISD, Mott Community College, public transit, "
            "and the airport.",
            f"What you actually pay depends on your home's taxable value and which of Burton's 7 school "
            f"districts you live in. On a home with ${EXAMPLE_TAXABLE:,} of taxable value (about a "
            f"$100,000 market value), the City's share is roughly ${city_dollars:,} a year; your full bill, "
            f"county and schools included, runs about ${lo_total:,}-${hi_total:,} depending on district.",
            "The City's own rate has held at 13.44 mills since 2022 and is down from 14.20 a decade ago. "
            "Burton has not raised its operating rate.",
        ],
    }

    panel = {
        "title": "Property Taxes",
        "subtitle": "Where your property tax bill actually goes",
        "summary": summary,
        "stats": stats,
        "charts": charts,
        "source": (
            "City of Burton audited financial statements (ACFR), Statistical Section: Direct and "
            "Overlapping Property Tax Rates (Genesee County Apportionment Report); and Michigan "
            "Department of Treasury, 2025 Total Property Tax Rates in Michigan."
        ),
        "links": [
            {"text": "City Finances dashboard", "href": "#finances"},
            {"text": "Genesee County Equalization (L-4029)",
             "href": "https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php"},
        ],
        "notes": [
            "Rates are in mills: dollars per $1,000 of TAXABLE value, which is usually about half of a "
            "home's market value. The breakdown is for a typical HOMESTEAD (owner-occupied) home; "
            "non-homestead/rental property pays about 18 mills more, almost all to schools.",
            "The City of Burton only sets and keeps the City portion (General, Police, Fire). Every other "
            "line is set by and sent to the county, schools, ISD, college, transit, or airport. The school "
            "amount varies by which of Burton's 7 districts you are in, so the \"Schools & State Education\" "
            "slice is the remainder for a representative district; the full per-authority split for your "
            "exact parcel is in the Genesee County Apportionment Report (L-4029).",
            "Source: City of Burton ACFR (FY2025) and Michigan Treasury 2025 Total Property Tax Rates. "
            "Public data; not a calculation of any individual tax bill.",
        ],
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  city {CITY_TOTAL} mills ({city_share}% of {HOMESTEAD_TOTAL}); schools+SET remainder {schools_set}")
    print(f"  city $ on ${EXAMPLE_TAXABLE:,} taxable = ${city_dollars:,}; full bill ${lo_total:,}-${hi_total:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
