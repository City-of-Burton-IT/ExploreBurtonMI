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

import argparse
import json
import os
import sys
from typing import Any, cast

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

ENTITY_ID = "2612060"  # Burton city (Census GEOID; confirmed against the API)
API = "https://micommunityfinancials.michigan.gov/api/component"
OUT = public_path("info-finances.json")
BUDGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-budget.json")

# --- City ADOPTED BUDGET (plan): from the City's General Ledger ------------------
# Decision 2026-10-06: the GL is the source of truth for adopted-budget figures.
# tools/Export-BsaBudget.ps1 writes tools/data/bsa-budget.json (aggregates only);
# build_budget_stats/build_budget_charts turn it into the dashboard pieces.
BUDGET_YEAR = "FY 2026-2027"
# Note: city millage lives on the Property Taxes dashboard, and pension/OPEB
# funded ratios on Financial Health, so no figure is shown on two dashboards.
CITY_STATS = [
    {"label": "Taxable value", "value": "$895.5M", "hint": "2026, city assessor"},
    {"label": "Full-time staff", "value": "102", "hint": "FY2026-27"},
]
FUND_CHART_SLICES = 12      # largest funds shown individually; the rest fold into one bar
GF_MIX_SLICES = 10          # departments shown individually in the General Fund donut


def load_budget_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_budget(raw, path)


def validate_budget(raw: Any, where: str = "budget file") -> dict:
    """Shape check at the trust boundary; anything implausible stops the build."""
    if not isinstance(raw, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "fiscal_year_end", "label", "totals", "funds", "general_fund"):
        if key not in raw:
            sys.exit(f"{where}: missing '{key}'")
    totals = raw["totals"]
    for key in ("revenue", "expenditure", "transfers_out"):
        if not isinstance(totals.get(key), int) or totals[key] < 0:
            sys.exit(f"{where}: totals.{key} must be a non-negative integer")
    if totals["expenditure"] <= 0:
        sys.exit(f"{where}: totals.expenditure must be positive")
    funds = raw["funds"]
    if not isinstance(funds, list) or len(funds) < 5:
        sys.exit(f"{where}: 'funds' must list at least five funds")
    for f in funds:
        for key in ("fund", "name"):
            if not isinstance(f.get(key), str) or not f[key].strip():
                sys.exit(f"{where}: fund entries need non-empty '{key}'")
        for key in ("revenue", "expenditure", "transfers_out"):
            if not isinstance(f.get(key), int) or f[key] < 0:
                sys.exit(f"{where}: fund {f.get('fund')} {key} must be a non-negative integer")
    if abs(sum(f["expenditure"] for f in funds) - totals["expenditure"]) > 1:
        sys.exit(f"{where}: fund expenditures do not add up to totals.expenditure")
    gf = raw["general_fund"]
    for key in ("revenue", "expenditure", "transfers_out"):
        if not isinstance(gf.get(key), int) or gf[key] < 0:
            sys.exit(f"{where}: general_fund.{key} must be a non-negative integer")
    for key in ("departments", "transfers"):
        rows = gf.get(key)
        if not isinstance(rows, list) or not rows:
            sys.exit(f"{where}: general_fund.{key} must be a non-empty list")
        for r in rows:
            if not isinstance(r.get("amount"), int) or r["amount"] < 0:
                sys.exit(f"{where}: general_fund.{key} amounts must be non-negative integers")
    if abs(sum(d["amount"] for d in gf["departments"]) - gf["expenditure"]) > 1:
        sys.exit(f"{where}: department amounts do not add up to general_fund.expenditure")
    return raw


def _m(v: int) -> str:
    return f"${v / 1e6:.1f}M"


_SMALL_WORDS = {"to", "of", "and", "for", "the", "in", "on"}


def _title(name: str) -> str:
    """'PARKS & RECREATION' -> 'Parks & Recreation'; tokens with digits (K9)
    stay as written and small words are lower-cased after the first word."""
    words = []
    for i, w in enumerate(name.strip().split()):
        if w == "&" or any(ch.isdigit() for ch in w):
            words.append(w)
        elif i > 0 and w.lower() in _SMALL_WORDS:
            words.append(w.lower())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def build_budget_stats(budget: dict) -> list:
    t, gf, label = budget["totals"], budget["general_fund"], budget["label"]
    return [
        {"label": "Total budget", "value": _m(t["expenditure"]),
         "hint": f"all funds, {label} adopted, City General Ledger"},
        {"label": "General Fund budget", "value": _m(gf["expenditure"]),
         "hint": f"{label} adopted; includes {_m(gf['transfers_out'])} in transfers to other funds"},
    ]


def build_budget_charts(budget: dict) -> list:
    t, gf, label = budget["totals"], budget["general_fund"], budget["label"]
    total = t["expenditure"]

    funds = sorted(budget["funds"], key=lambda f: f["expenditure"], reverse=True)
    shown = [f for f in funds if f["expenditure"] > 0][:FUND_CHART_SLICES]
    rest = total - sum(f["expenditure"] for f in shown)
    fund_series = [{"label": _title(f["name"]), "value": round(100 * f["expenditure"] / total, 1)} for f in shown]
    if rest > 0:
        fund_series.append({"label": "All other funds", "value": round(100 * rest / total, 1)})

    # General Fund mix: departments, with the transfers-out department (999)
    # expanded into where the money goes, so "Transfer to Fire" reads as such.
    gf_total = gf["expenditure"]
    slices: list[tuple[str, int]] = []
    for d in gf["departments"]:
        name = d["name"].strip()
        if not name or d["code"] == "999":
            continue
        slices.append((_title(name), d["amount"]))
    transfers = sorted(gf["transfers"], key=lambda r: r["amount"], reverse=True)
    for r in transfers[:4]:
        nm = _title(r["name"]).replace("Transfer out to ", "Transfer to ")
        slices.append((nm, r["amount"]))
    other_xfer = sum(r["amount"] for r in transfers[4:])
    if other_xfer > 0:
        slices.append(("Other transfers to City funds", other_xfer))
    slices.sort(key=lambda sl: sl[1], reverse=True)
    head, tail = slices[:GF_MIX_SLICES], slices[GF_MIX_SLICES:]
    unaccounted = gf_total - sum(a for _, a in slices)
    other = sum(a for _, a in tail) + max(unaccounted, 0)
    mix_series = [{"label": n, "value": round(100 * a / gf_total, 1)} for n, a in head]
    if other > 0:
        mix_series.append({"label": "Other departments and transfers", "value": round(100 * other / gf_total, 1)})

    return [
        {"type": "bars", "title": f"{label} adopted budget by fund (all funds)", "unit": "%", "series": fund_series},
        {"type": "donut", "title": f"General Fund spending mix, {label} (plan)", "unit": "%", "series": mix_series},
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


AUDITED_STAT_LABELS = ("General Fund revenues", "General Fund expenditures", "Long-term debt", "General Fund reserve")


def reuse_audited(existing_path: str) -> tuple[list, list, int | None]:
    """Offline mode: keep the committed audited stats and trend charts untouched
    when the State API is unreachable, so a GL refresh never erases them."""
    with open(existing_path, encoding="utf-8") as fh:
        panel = json.load(fh)
    health = [st for st in panel.get("stats", []) if st.get("label") in AUDITED_STAT_LABELS]
    trends = [c for c in panel.get("charts", []) if c.get("type") == "trend" and "audited" in c.get("title", "")]
    year = None
    for st in health:
        hint = st.get("hint", "")
        if hint.startswith("audited FY"):
            try:
                year = int(hint[len("audited FY"):len("audited FY") + 4])
            except ValueError:
                pass
            break
    if not health or not trends:
        sys.exit(f"{existing_path}: no audited stats/trends to reuse; run online instead")
    return health, trends, year


def main() -> int:
    ap = argparse.ArgumentParser(description="Build info-finances.json")
    ap.add_argument("--budget-file", default=BUDGET_FILE,
                    help="GL aggregate export from tools/Export-BsaBudget.ps1 (default: tools/data/bsa-budget.json)")
    ap.add_argument("--offline", action="store_true",
                    help="reuse the audited stats and trends already in public/info-finances.json "
                         "instead of calling the State API")
    args = ap.parse_args()

    budget = load_budget_file(args.budget_file)
    if args.offline:
        health, trends, latest_year = reuse_audited(OUT)
    else:
        snapshot = fetch_snapshot()
        analytics = fetch_analytics()
        trends, latest_year = build_trends(snapshot)
        health = build_health_stats(snapshot, analytics, latest_year)
    budget_stats = build_budget_stats(budget)
    budget_charts = build_budget_charts(budget)

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
        "stats": budget_stats + CITY_STATS + health,
        "charts": [revenue_chart] + budget_charts + trends,
        "source": (
            f"City of Burton General Ledger (BS&A) for the {budget['label']} adopted-budget figures "
            f"(aggregates extracted {budget['extracted']}); City of Burton {BUDGET_YEAR} Approved Budget "
            "(Controller's Office) for taxable value and staffing; State of Michigan Community Financials "
            "(audited F-65 actuals) for the historical trends."
        ),
        "links": [
            {
                "text": "Michigan Community Financials dashboard",
                "href": f"https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/{ENTITY_ID}",
            },
            {"text": "City of Burton", "href": "https://www.burtonmi.gov"},
        ],
        "notes": [
            "Two views: the FY2026-27 figures and fund/spending charts are the city's ADOPTED BUDGET as recorded "
            "in the City's General Ledger (original appropriations before amendments; a plan, all funds unless "
            "noted General Fund). The dollar trends are AUDITED ACTUALS reported to the State of Michigan, which "
            "run about a year behind the adopted budget; the two are not the same measure.",
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
