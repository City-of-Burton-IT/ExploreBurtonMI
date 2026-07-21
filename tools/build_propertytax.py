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

import sys

from lib.iox import write_json
from lib.paths import public_path

OUT = public_path("info-propertytax.json")

# --- Provisional City rate pending the current L-4029 ---------------------------
CITY_RATE_PERIOD = "Provisional — current L-4029 pending"
FULL_BILL_RATE_PERIOD = "2025 published rates"

# Retain the last supported exact rate underneath the resident-facing 13.4 display.
# Do not substitute the Approved Budget's 13.2948 service-line sum for a certified
# levy; update this value and replace the reconciliation row when the L-4029 arrives.
CITY_TOTAL = 13.44

# FY2026-27 Approved Budget service-line reference. These rows do not fully
# reconcile to the provisional 13.44 total, so the difference remains explicit
# rather than being assigned to a service without the certified L-4029.
CITY_GENERAL = 4.0000
CITY_POLICE = 8.3159
CITY_FIRE = 0.9789
BUDGET_SERVICE_TOTAL = round(CITY_GENERAL + CITY_POLICE + CITY_FIRE, 4)
RECONCILIATION_DIFFERENCE = round(CITY_TOTAL - BUDGET_SERVICE_TOTAL, 4)

BREAKDOWN_NOTE = (
    "The provisional City estimate uses the last supported 13.44-mill rate, shown "
    "as 13.4. The FY2026-27 Approved Budget lists General 4.0000, aggregate Police "
    "8.3159, and Fire 0.9789 mills (13.2948 total), and those budget lines are "
    "shown as budget-reference rows. Their 0.1452-mill difference from the "
    "provisional total is not assigned to a service while the current L-4029 "
    "is pending."
)

# The latest complete published district totals are still 2025. Use their City
# component only for the 2025 authority chart; never subtract the adopted levy
# from a 2025 complete-bill total.
PUBLISHED_2025_CITY_TOTAL = 13.44

CITY_LEVIES = [
    {
        "id": "general-operating",
        "service": "General city operations",
        "authorization": "City Charter — budget reference",
        "description": "FY2026-27 Approved Budget service line.",
        "mills": CITY_GENERAL,
        "voterApproved": False,
    },
    {
        "id": "police",
        "service": "Police services",
        "authorization": "Voter approved — budget aggregate",
        "description": "FY2026-27 Approved Budget aggregate Police Levies line.",
        "mills": CITY_POLICE,
        "voterApproved": True,
    },
    {
        "id": "fire",
        "service": "Fire services",
        "authorization": "Voter approved — budget reference",
        "description": "FY2026-27 Approved Budget service line.",
        "mills": CITY_FIRE,
        "voterApproved": True,
    },
    {
        "id": "l4029-reconciliation",
        "service": "Unassigned difference",
        "authorization": "Pending L-4029",
        "description": (
            "Difference between the 13.44 provisional total and 13.2948 "
            "budget service-line total."
        ),
        "mills": RECONCILIATION_DIFFERENCE,
        "voterApproved": False,
    },
]

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


def build_estimator() -> dict:
    return {
        "cityRatePeriod": CITY_RATE_PERIOD,
        "fullBillRatePeriod": FULL_BILL_RATE_PERIOD,
        "cityMills": CITY_TOTAL,
        "cityLevies": CITY_LEVIES,
        "districts": [
            {"name": name, "homestead": hs, "nonHomestead": nhs}
            for name, hs, nhs in DISTRICT_RATES
        ],
    }


def main() -> int:
    uniform = PUBLISHED_2025_CITY_TOTAL + COUNTY + MOTT + ISD + MTA + AIRPORT
    schools_set = round(HOMESTEAD_TOTAL - uniform, 2)  # remainder = schools + State Ed

    city_dollars = CITY_TOTAL * EXAMPLE_TAXABLE / 1000
    lo_total = round(DISTRICT_HOMESTEAD[0][1] * EXAMPLE_TAXABLE / 1000)
    hi_total = round(DISTRICT_HOMESTEAD[-1][1] * EXAMPLE_TAXABLE / 1000)

    stats = [
        {
            "label": "City of Burton's rate",
            "value": f"{CITY_TOTAL:.1f} mills",
            "hint": "Provisional display; last supported exact rate is 13.44",
        },
        {
            "label": "Rate status",
            "value": "Provisional",
            "hint": "Replace when the current certified L-4029 is available",
        },
        {
            "label": "City tax on a $50k-taxable home",
            "value": f"${round(city_dollars):,}/yr",
            "hint": "Provisional 13.44-mill rate; about a $100,000 market-value home",
        },
        {
            "label": "School districts in Burton",
            "value": "7",
            "hint": "2025 complete-bill rates vary by district",
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
    ]

    summary = {
        "heading": "What this means for you",
        "body": [
            (
                f"Burton's City rate is shown provisionally as {CITY_TOTAL:.1f} mills, "
                f"using the last supported exact rate of {CITY_TOTAL:.2f}. The current "
                "certified L-4029 is pending and will replace this figure when available."
            ),
            (
                f"At ${EXAMPLE_TAXABLE:,} of taxable value, the City portion is about "
                f"${round(city_dollars):,} a year. The latest complete published bill rates "
                f"are from 2025 and range from about ${lo_total:,} to ${hi_total:,} at that "
                "taxable value, depending on school district."
            ),
            (
                f"The estimator shows the Approved Budget's General ({CITY_GENERAL:.4f}), "
                f"aggregate Police ({CITY_POLICE:.4f}), and Fire ({CITY_FIRE:.4f}) lines. "
                f"Their {BUDGET_SERVICE_TOTAL:.4f}-mill subtotal leaves "
                f"{RECONCILIATION_DIFFERENCE:.4f} mills unassigned pending the L-4029."
            ),
            (
                "County, schools, the State, ISD, college, transit, airport, and other "
                "authorities receive their own portions; those amounts do not become City revenue."
            ),
        ],
    }

    estimator = build_estimator()

    panel = {
        "title": "Property Taxes",
        "subtitle": "Where your property tax bill actually goes",
        "summary": summary,
        "estimator": estimator,
        "stats": stats,
        "charts": charts,
        "source": (
            "City of Burton audited financial statements for the 13.44-mill historical "
            "rate; Michigan Department of Treasury, 2025 Total Property Tax Rates in "
            "Michigan; and City of Burton FY2026-27 Approved Budget, Tax Millage, as an "
            "uncertified service-line reference pending the current L-4029."
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
            BREAKDOWN_NOTE,
            (
                "The complete-bill district estimate and authority chart use 2025 published "
                "rates and are kept separately dated from the provisional City rate."
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
    print(
        f"  Provisional City {CITY_TOTAL:.2f} mills (displayed {CITY_TOTAL:.1f}); "
        "current L-4029 pending"
    )
    print(f"  2025 complete-bill districts: {len(DISTRICT_RATES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
