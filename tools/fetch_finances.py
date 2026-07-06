"""Build public/info-finances.json for the City of Burton Finances dashboard.

Two clearly-separated zones (the city's own ADOPTED BUDGET vs the State's AUDITED
ACTUALS) so a resident never conflates a plan with a result, or a General-Fund
figure with an all-funds figure:

  * Adopted budget (plan): the city's current adopted-budget detail, total by
    fund and General-Fund spending mix. Held as constants below; update once a
    year when a new budget is adopted (the scanned budget PDFs have no usable
    text layer, so this can't be auto-extracted).
  * Financial history (audited actuals): pulled live from the State of Michigan
    "Community Financials" API (the same data behind
    micommunityfinancials.michigan.gov), which publishes each city's audited
    F-65 figures as a clean multi-year series, 2010 to the latest audited year.
    This is the authoritative, census-like source for trends + fiscal health.

Re-runnable (committed output; the site reads the JSON, never the API):
    python tools/fetch_finances.py

Uses the shared tools/lib helpers (HTTP retry, atomic writes).
"""
from __future__ import annotations

import sys
from typing import Any, cast

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

ENTITY_ID = "2612060"  # Burton city (Census GEOID; confirmed against the API)
API = "https://micommunityfinancials.michigan.gov/api/component"
OUT = public_path("info-finances.json")

# --- City ADOPTED BUDGET (plan): update yearly from the adopted budget --------
BUDGET_YEAR = "FY 2026-2027"
# Note: city millage lives on the Property Taxes dashboard, and pension/OPEB
# funded ratios on Financial Health, so no figure is shown on two dashboards.
CITY_STATS = [
    {"label": "Total budget", "value": "$67.7M", "hint": "all funds, FY2026-27 adopted"},
    {"label": "Taxable value", "value": "$895.5M", "hint": "2026, city assessor"},
    {"label": "Full-time staff", "value": "102", "hint": "FY2026-27"},
]
CITY_CHARTS = [
    {
        "type": "bars",
        "title": "FY2026-27 adopted budget by fund (all funds)",
        "unit": "%",
        "series": [
            {"label": "Major Streets", "value": 21},
            {"label": "Police Fund", "value": 17},
            {"label": "Watermain", "value": 13},
            {"label": "Sanitary Sewer", "value": 13},
            {"label": "General Fund", "value": 13},
            {"label": "Local Streets", "value": 6},
            {"label": "Fire Fund", "value": 4},
            {"label": "Self Insurance", "value": 4},
            {"label": "Motor Pool", "value": 3},
            {"label": "Rubbish Collection", "value": 3},
            {"label": "Senior Citizens", "value": 1},
            {"label": "Building", "value": 1},
            {"label": "Information Technology", "value": 1},
        ],
    },
    {
        "type": "donut",
        "title": "General Fund spending mix, FY2026-27 (plan)",
        "unit": "%",
        "series": [
            {"label": "Legacy cost payment", "value": 29},
            {"label": "Seniors & Library", "value": 19},
            {"label": "Fire transfer", "value": 18},
            {"label": "Street lighting", "value": 16},
            {"label": "Parks & Recreation", "value": 11},
            {"label": "Police transfer", "value": 7},
        ],
    },
]

# --- Revenue by source (AUDITED ACFR, governmental funds, FY ended 6/30/2025) ----
# From the City of Burton audited financial statements (ACFR), Governmental Funds
# Statement of Revenue, Total Governmental Funds column. These are the city's
# day-to-day (tax-and-state-supported) funds; water & sewer are enterprise funds
# paid by usage bills and are NOT included here. Update yearly from the new ACFR.
REVENUE_FY = "FY2025"
REVENUE_TOTAL_M = 27.0
REVENUE_SOURCES = [
    ("Property taxes", 10.64),
    ("State road funds (Act 51)", 5.46),
    ("State-shared revenue", 3.59),
    ("Special assessments", 2.15),
    ("Fees & charges", 1.39),
    ("Investment income", 1.40),
    ("Grants", 1.27),
    ("Other", 1.12),
]
PROPERTY_TAX_SHARE = 39  # property taxes as % of governmental revenue

# --- State AUDITED ACTUALS (from the Community Financials snapshot) --------------
# Multi-year trend charts: (snapshot dimension name, chart title, divide-to-millions).
TREND_SERIES = [
    ("Total Taxable Value", "Total taxable value (audited, $M)"),
    ("Total General Fund Revenues", "General Fund revenues (audited, $M)"),
    ("Total General Fund Expenditures", "General Fund expenditures (audited, $M)"),
    ("Long Term Debt", "Long-term debt (audited, $M)"),
    ("Unfunded Pension Liability", "Unfunded pension liability (audited, $M)"),
]


# --- Interactive explainer: how municipal budgeting works ------------------------
# Plain-language adaptation of "Funds, Fund Balance, and Budgeting Concepts," a
# presentation to the City of Burton by Plante Moran (Pam Hill, CPA; Steven
# Pochini, CPA). Rendered as an expandable "learn how this works" element.
BUDGET_EXPLAINER = {
    "title": "How city budgeting works",
    "intro": "A quick, plain-language guide to the terms behind these numbers.",
    "items": [
        {"term": "What is a \"fund\"?",
         "body": "The city keeps its money in separate \"funds\", like labeled envelopes, so each "
                 "dollar is spent only on what it's meant for. Money raised for roads, police, or "
                 "seniors is tracked separately to prove it was used as promised."},
        {"term": "The General Fund",
         "body": "The General Fund is the city's main, most-flexible account: the money not tied to a "
                 "specific purpose, used for general services. It's usually the most closely watched fund."},
        {"term": "Types of funds",
         "body": "Burton has governmental funds (General, streets, police, fire, parks and more) and "
                 "enterprise funds that run like a business and pay their own way: water and sewer, "
                 "funded by usage bills rather than taxes."},
        {"term": "What is \"fund balance\"?",
         "body": "Fund balance is the city's savings in a fund, what it owns minus what it owes. It's "
                 "the cushion for emergencies, big purchases, and steady cash flow, and much of it is "
                 "restricted by law to a specific use."},
        {"term": "How much savings is healthy?",
         "body": "There's no single right number, but most governments aim to keep 10-20% of a year's "
                 "spending in reserve. The GFOA suggests at least about 17%; Michigan's fiscal-stress "
                 "test uses 13% as a floor."},
        {"term": "What \"balanced budget\" really means",
         "body": "It means the city plans to end the year with a positive fund balance, not that "
                 "spending must exactly equal revenue. In some years it's appropriate to spend down "
                 "savings for a planned project."},
        {"term": "Appropriations (the spending limit)",
         "body": "When the budget is adopted, the city sets \"appropriations\", the legal maximum each "
                 "department may spend. It's a ceiling, not a forecast, and by state law the city can't "
                 "spend money it hasn't appropriated."},
    ],
    "source": ("Adapted from \"Funds, Fund Balance, and Budgeting Concepts,\" a presentation to the "
               "City of Burton by Plante Moran (Pam Hill, CPA; Steven Pochini, CPA)."),
}


def _get(url: str) -> Any:
    return get_json(url, timeout=40)


def fetch_snapshot() -> dict:
    return cast(dict, _get(f"{API}/snapshot.json?component_index=3&entity_id={ENTITY_ID}&filter_type=CITY"))


def fetch_analytics() -> list:
    return cast(list, _get(f"{API}/analytics.json?component_index=4&entity_id={ENTITY_ID}&filter_type=CITY&year=2025"))


def _series_by_name(snapshot: dict, name: str):
    for item in snapshot.get("data", []):
        if item.get("dimension", {}).get("name") == name:
            return item.get("values", [])
    return []


def build_trends(snapshot: dict) -> tuple[list, int | None]:
    years = snapshot.get("years", [])
    charts = []
    latest_year = years[-1] if years else None
    for name, title in TREND_SERIES:
        values = _series_by_name(snapshot, name)
        pairs = [(y, v) for y, v in zip(years, values) if v is not None]
        # Drop leading zeros: a $0 in an early year is "not yet reported" (e.g.
        # pension UAL before the state required it), not a real $0 figure, and
        # would misleadingly read as a value appearing from nothing.
        while len(pairs) > 1 and pairs[0][1] == 0:
            pairs.pop(0)
        points = [{"x": str(y), "y": round(v / 1_000_000, 1)} for y, v in pairs]
        if len(points) >= 2:
            charts.append({"type": "trend", "title": title, "unit": "$M", "points": points})
    return charts, latest_year


def _latest(snapshot: dict, name: str):
    vals = [v for v in _series_by_name(snapshot, name) if v is not None]
    return vals[-1] if vals else None


def build_health_stats(snapshot: dict, analytics: list, year: int | None) -> list:
    stats = []
    rev = _latest(snapshot, "Total General Fund Revenues")
    exp = _latest(snapshot, "Total General Fund Expenditures")
    debt = _latest(snapshot, "Long Term Debt")
    yr = f"audited FY{year}" if year else "audited"
    if rev is not None:
        stats.append({"label": "General Fund revenues", "value": f"${rev / 1e6:.1f}M", "hint": yr})
    if exp is not None:
        stats.append({"label": "General Fund expenditures", "value": f"${exp / 1e6:.1f}M", "hint": yr})
    if debt is not None:
        stats.append({"label": "Long-term debt", "value": f"${debt / 1e6:.1f}M", "hint": yr})

    # General Fund Ratio (reserves / revenues) + statewide rank, from analytics.
    for a in analytics:
        if a.get("key_entity") == "general_fund_ratio" and a.get("value") is not None:
            pct = round(a["value"] * 100)
            hint = "reserves vs. revenues; higher is better"
            if a.get("rank") and a.get("total"):
                hint = f"reserves vs. revenues; ranks {int(a['rank'])} of {int(a['total'])} MI cities (higher is better)"
            stats.append({"label": "General Fund reserve", "value": f"{pct}%", "hint": hint})
            break
    return stats


def main() -> int:
    snapshot = fetch_snapshot()
    analytics = fetch_analytics()
    trends, latest_year = build_trends(snapshot)
    health = build_health_stats(snapshot, analytics, latest_year)

    revenue_chart = {
        "type": "bars",
        "title": f"Revenue by source ({REVENUE_FY} audited, governmental funds, $M)",
        "unit": "$M",
        "series": [{"label": lbl, "value": v} for lbl, v in REVENUE_SOURCES],
    }

    summary = {
        "heading": "What this means for you",
        "body": [
            f"Property taxes cover only about {PROPERTY_TAX_SHARE}% of the city's day-to-day "
            f"(governmental) budget. The rest comes from state road funding (the Act 51 gas and "
            "weight tax), state-shared revenue, special assessments, fees, and grants. A big "
            "share of what runs the city is paid by the state and by users of specific services, "
            "not by local property taxes.",
            "Water and sewer service is separate: it is an enterprise paid for by usage bills, not "
            "taxes, so it is not part of these figures. (See the Property Taxes dashboard for how a "
            "tax bill splits among the city, county, and schools, and Financial Health for debt and "
            "pensions.)",
        ],
    }

    panel = {
        "title": "City Finances",
        "subtitle": f"{BUDGET_YEAR} adopted budget + audited financial history",
        "summary": summary,
        "explainer": BUDGET_EXPLAINER,
        "stats": CITY_STATS + health,
        "charts": [revenue_chart] + CITY_CHARTS + trends,
        "source": (
            f"City of Burton {BUDGET_YEAR} Approved Budget (Controller's Office) for the adopted-budget "
            "figures; State of Michigan Community Financials (audited F-65 actuals) for the historical trends."
        ),
        "links": [
            {
                "text": "Michigan Community Financials dashboard",
                "href": f"https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/{ENTITY_ID}",
            },
            {"text": "City of Burton", "href": "https://www.burtonmi.gov"},
        ],
        "notes": [
            "Two views: the FY2026-27 figures and fund/spending charts are the city's ADOPTED BUDGET (a plan, "
            "all funds unless noted General Fund). The dollar trends are AUDITED ACTUALS reported to the State "
            "of Michigan, which run about a year behind the adopted budget; the two are not the same measure.",
            "General Fund figures cover only the General Fund, not the city's total all-funds budget.",
            "Audited trends and fiscal-health figures come from the State of Michigan Community Financials "
            "program (audited F-65 annual financial reports).",
        ],
    }

    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  latest audited year: {latest_year}")
    print(f"  stats: {len(panel['stats'])}  charts: {len(panel['charts'])} ({len(trends)} state trends)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
