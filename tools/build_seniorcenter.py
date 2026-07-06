"""Build public/info-seniorcenter.json: the Burton Senior Center dashboard.

The figures below are the center's own activity records for CALENDAR YEAR 2025,
exported from its check-in / membership system (My Senior Center). They are held
as constants and refreshed once a year from five exports the Senior Center staff
provide (kept out of git: they are operational exports, not web data):

  * ExcelAvgAttendance.xls  -> attendance (check-ins, avg per day, by month)
  * ExcelExport (1).xls      -> active-member demographics (age, where they live)
  * ExcelExport (2).xls      -> event/program sign-ins and hours by category
  * ExcelExport.xls          -> rides provided (senior transportation)
  * ExcelExport (3).xls      -> volunteer hours and pay-equivalent value

To refresh next year: open the new exports, update the constants in the "SOURCE
DATA" block below, and re-run. No PII, every figure is an aggregate count.

Re-runnable (committed output; the site reads the JSON, never the exports):
    python tools/build_seniorcenter.py

Uses the shared tools/lib helpers (repo paths, atomic writes).
"""
from __future__ import annotations

import sys

from lib.iox import write_json
from lib.paths import public_path

OUT = public_path("info-seniorcenter.json")

# ---------------------------------------------------------------------------
# SOURCE DATA: Burton Senior Center, calendar year 2025. Refresh yearly.
# ---------------------------------------------------------------------------
YEAR = "2025"
MEMBERS = 1564          # active members in 2025
CHECKINS = 28710        # total visits (each attendance counted)
OPEN_DAYS = 248
AVG_PER_DAY = 116       # 115.77 rounded

PROGRAM_SIGNINS = 28707
PROGRAM_HOURS = 131052  # 131,051.75 rounded

VOL_HOURS = 4615        # 4,614.58 rounded
VOL_VALUE = 69046       # pay-equivalent $, 69,046.25 rounded
VOL_PEOPLE = 51

RIDES = 1499            # transportation rides provided
RIDERS = 114            # unique riders

# Program sign-ins by category (Duplicated count). Largest first.
PROGRAMS = [
    ("Socialization", 9734),
    ("Nutrition & meals", 7913),
    ("Health & fitness", 5202),
    ("Social services", 2447),
    ("Outreach", 1934),
    ("Education", 1409),
]

# Average daily attendance by month (avg per open day).
MONTHLY = [
    ("Jan", 109.1), ("Feb", 111.1), ("Mar", 138.1), ("Apr", 133.7),
    ("May", 121.7), ("Jun", 142.4), ("Jul", 132.1), ("Aug", 128.2),
    ("Sep", 34.4), ("Oct", 100.0), ("Nov", 123.9), ("Dec", 114.3),
]

# Active members by age band (in age order).
AGE_BANDS = [
    ("Under 55", 32), ("55-59", 44), ("60-64", 153), ("65-69", 274),
    ("70-74", 329), ("75-79", 323), ("80-84", 208), ("85+", 201),
]

IN_TOWN = 442
OUT_OF_TOWN = 1122
LIVES_ALONE_PCT = 52     # 52.4% live alone
FEMALE_PCT = 72          # 71.5%


def main() -> int:
    out_pct = round(OUT_OF_TOWN / MEMBERS * 100)

    stats = [
        {"label": "Members served", "value": f"{MEMBERS:,}", "hint": f"active members, {YEAR}"},
        {"label": "Visits", "value": f"{CHECKINS:,}", "hint": f"~{AVG_PER_DAY} per open day ({OPEN_DAYS} days)"},
        {"label": "Program hours", "value": f"{PROGRAM_HOURS:,}", "hint": f"across {PROGRAM_SIGNINS:,} program sign-ins"},
        {"label": "Volunteer value", "value": f"${VOL_VALUE:,}", "hint": f"{VOL_HOURS:,} hours from {VOL_PEOPLE} volunteers"},
    ]

    charts = [
        {"type": "bars", "title": "Program sign-ins by category", "unit": "",
         "series": [{"label": lbl, "value": v} for lbl, v in PROGRAMS]},
        {"type": "trend", "title": "Average daily attendance by month", "unit": "",
         "points": [{"x": m, "y": v} for m, v in MONTHLY]},
        {"type": "bars", "title": "Members by age", "unit": "",
         "series": [{"label": lbl, "value": v} for lbl, v in AGE_BANDS]},
        {"type": "donut", "title": "Where members live",
         "series": [
             {"label": "In Burton", "value": IN_TOWN, "color": "#2c57a0"},
             {"label": "Outside Burton", "value": OUT_OF_TOWN, "color": "#4ea735"},
         ]},
    ]

    summary = {
        "heading": "What this means for you",
        "body": [
            f"The Burton Senior Center is one of the busiest in the region. In {YEAR} it served "
            f"{MEMBERS:,} members with about {CHECKINS:,} visits, an average of {AVG_PER_DAY} people "
            f"every day it was open. Nearly three-quarters of members ({out_pct}%) come from outside "
            "the city, so Burton's center is a hub for older adults across the surrounding area.",
            f"It is far more than a place to gather: the center ran nutrition, health-and-fitness, "
            f"social-service, and outreach programs totaling more than {PROGRAM_HOURS:,} hours in {YEAR}, "
            f"and provided about {RIDES:,} rides for grocery trips, appointments, and getting to and from "
            f"the center. Just over half of members ({LIVES_ALONE_PCT}%) live alone, so for many it is a "
            "primary source of meals, activity, and connection.",
            f"Much of this runs on volunteers: {VOL_PEOPLE} people gave about {VOL_HOURS:,} hours in {YEAR} "
            f"(roughly ${VOL_VALUE:,} of donated time), staffing bingo, the kitchen, tax help, and the "
            "reception desk.",
        ],
    }

    panel = {
        "title": "Burton Senior Center",
        "subtitle": f"Who it serves and what it offers: calendar year {YEAR}",
        "summary": summary,
        "stats": stats,
        "charts": charts,
        "source": (
            f"City of Burton Senior Center activity records (member check-in and program system), "
            f"calendar year {YEAR}."
        ),
        "links": [
            {"text": "Burton Senior Center", "href": "https://www.burtonmi.gov/government/senior_center/index.php"},
            {"text": "Finances dashboard", "href": "#finances"},
        ],
        "notes": [
            "\"Visits\" and \"program sign-ins\" count every attendance (one person is counted each time "
            "they come); \"members\" and \"volunteers\" count each person once. Members may live outside "
            "the city: the center serves older adults across the surrounding area, not Burton residents "
            "only.",
            f"Volunteer value is the center's pay-equivalent estimate of donated hours, not money spent. "
            f"Monthly figures are the average attendance per open day; the center was open {OPEN_DAYS} days "
            f"in {YEAR}.",
            f"Source: City of Burton Senior Center, {YEAR} activity records. Aggregate counts only, no "
            "personal information.",
        ],
    }

    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  members {MEMBERS:,}  visits {CHECKINS:,}  program hours {PROGRAM_HOURS:,}")
    print(f"  volunteers {VOL_PEOPLE} ({VOL_HOURS:,}h ${VOL_VALUE:,})  rides {RIDES:,}  out-of-town {out_pct}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
