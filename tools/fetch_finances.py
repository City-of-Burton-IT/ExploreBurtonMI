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
OUT_HISTORY = public_path("info-financehistory.json")
BUDGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-budget.json")
TAXROLL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-taxroll.json")
HERE = os.path.dirname(os.path.abspath(__file__))
SPEND_FILE = os.path.join(HERE, "data", "bsa-spend.json")

# --- City ADOPTED BUDGET (plan): from the City's General Ledger ------------------
# Decision 2026-10-06: the GL is the source of truth for adopted-budget figures.
# tools/Export-BsaBudget.ps1 writes tools/data/bsa-budget.json (aggregates only);
# build_budget_stats/build_budget_charts turn it into the dashboard pieces.
BUDGET_YEAR = "FY 2026-2027"
# Note: city millage lives on the Property Taxes dashboard, and pension/OPEB
# funded ratios on Financial Health, so no figure is shown on two dashboards.
CITY_STATS = [
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
    actuals = raw.get("actuals")
    if actuals is not None:
        if not isinstance(actuals, dict):
            sys.exit(f"{where}: 'actuals' must be an object")
        prior = actuals.get("prior_year")
        if not isinstance(prior, dict) or not isinstance(prior.get("funds"), list) or not prior["funds"]:
            sys.exit(f"{where}: actuals.prior_year.funds must be a non-empty list")
        for key in ("fiscal_year_end", "label"):
            if key not in prior:
                sys.exit(f"{where}: actuals.prior_year.{key} missing")
        for f in prior["funds"]:
            for key in ("revenue_budget", "expenditure_budget", "revenue_actual", "expenditure_actual"):
                if not isinstance(f.get(key), int):
                    sys.exit(f"{where}: actuals.prior_year fund {f.get('fund')} {key} must be an integer")
        ytd = actuals.get("year_to_date")
        if ytd is not None:
            for key in ("through", "months", "funds"):
                if key not in ytd:
                    sys.exit(f"{where}: actuals.year_to_date.{key} missing")
            for f in ytd["funds"]:
                for key in ("revenue_actual", "expenditure_actual"):
                    if not isinstance(f.get(key), int):
                        sys.exit(f"{where}: actuals.year_to_date fund {f.get('fund')} {key} must be an integer")
    history = raw.get("history")
    if history is not None:
        if not isinstance(history, list) or len(history) < 5:
            sys.exit(f"{where}: 'history' must list at least five fiscal years")
        years = []
        for row in history:
            if not isinstance(row.get("fiscal_year_end"), int):
                sys.exit(f"{where}: history rows need an integer fiscal_year_end")
            years.append(row["fiscal_year_end"])
            for block, keys in (("general_fund", ("revenue_actual", "expenditure_actual", "revenue_amended", "expenditure_amended")),
                                ("all_funds", ("revenue_actual", "expenditure_actual", "expenditure_amended"))):
                b = row.get(block)
                if not isinstance(b, dict):
                    sys.exit(f"{where}: history {row['fiscal_year_end']} missing {block}")
                for key in keys:
                    if not isinstance(b.get(key), int):
                        sys.exit(f"{where}: history {row['fiscal_year_end']} {block}.{key} must be an integer")
        if years != sorted(set(years)):
            sys.exit(f"{where}: history years must be ascending and unique")
    return raw


def load_taxroll_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_taxroll(raw, path)


def validate_taxroll(raw: Any, where: str = "tax-roll file") -> dict:
    if not isinstance(raw, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "tax_year", "taxable_value"):
        if key not in raw:
            sys.exit(f"{where}: missing '{key}'")
    tv = raw["taxable_value"]
    if not isinstance(tv.get("total"), int) or tv["total"] <= 0:
        sys.exit(f"{where}: taxable_value.total must be a positive integer")
    groups = tv.get("by_group")
    if not isinstance(groups, list) or not groups:
        sys.exit(f"{where}: taxable_value.by_group must be a non-empty list")
    for g in groups:
        if not isinstance(g.get("group"), str) or not isinstance(g.get("taxable"), int) or g["taxable"] < 0:
            sys.exit(f"{where}: taxable_value.by_group entries need a group name and integer taxable")
    if abs(sum(g["taxable"] for g in groups) - tv["total"]) > 1:
        sys.exit(f"{where}: taxable_value groups do not add up to the total")
    hist = tv.get("history")
    if not isinstance(hist, list) or len(hist) < 2:
        sys.exit(f"{where}: taxable_value.history must list at least two years")
    years = [h.get("year") for h in hist]
    if years != sorted(set(years)) or not all(isinstance(h.get("taxable"), int) for h in hist):
        sys.exit(f"{where}: taxable_value.history must be ascending unique years with integer taxable")
    return raw


ACTUALS_FUND_SLICES = 8   # funds shown individually in the budget-vs-actual chart


def build_actuals(budget: dict) -> tuple[list, list]:
    """Stats and charts for 'how did last year turn out' and 'how is this year going'."""
    actuals = budget.get("actuals")
    if not actuals:
        return [], []
    prior = actuals["prior_year"]
    label = prior["label"]
    gf = next((f for f in prior["funds"] if f["fund"] == "101"), None)
    stats: list = []
    charts: list = []
    if gf:
        stats.append({
            "label": f"General Fund result, {label}",
            "value": _m(gf["revenue_actual"] - gf["expenditure_actual"]).replace("$-", "-$"),
            "hint": (f"actual revenue {_m(gf['revenue_actual'])} minus spending {_m(gf['expenditure_actual'])}; "
                     f"a negative figure was covered from reserves"),
        })
        charts.append({
            "type": "compare",
            "title": f"General Fund, {label}: budget vs actual ($M)",
            "rows": [
                {"label": "Revenue", "unit": "$M",
                 "values": [{"name": "Budget", "value": round(gf["revenue_budget"] / 1e6, 2)},
                            {"name": "Actual", "value": round(gf["revenue_actual"] / 1e6, 2)}]},
                {"label": "Spending", "unit": "$M",
                 "values": [{"name": "Budget", "value": round(gf["expenditure_budget"] / 1e6, 2)},
                            {"name": "Actual", "value": round(gf["expenditure_actual"] / 1e6, 2)}]},
            ],
        })
    top = sorted((f for f in prior["funds"] if f["expenditure_budget"] > 0),
                 key=lambda f: f["expenditure_budget"], reverse=True)[:ACTUALS_FUND_SLICES]
    if top:
        charts.append({
            "type": "compare",
            "title": f"Spending by fund, {label}: budget vs actual ($M)",
            "rows": [
                {"label": _title(f["name"]), "unit": "$M",
                 "values": [{"name": "Budget", "value": round(f["expenditure_budget"] / 1e6, 2)},
                            {"name": "Actual", "value": round(f["expenditure_actual"] / 1e6, 2)}]}
                for f in top
            ],
        })
    ytd = actuals.get("year_to_date")
    if ytd:
        gf_ytd = next((f for f in ytd["funds"] if f["fund"] == "101"), None)
        gf_plan = budget["general_fund"]
        if gf_ytd and gf_plan["expenditure"] > 0:
            pct = round(100 * gf_ytd["expenditure_actual"] / gf_plan["expenditure"])
            elapsed = round(100 * int(ytd["months"]) / 12)
            stats.append({
                "label": "General Fund spending so far",
                "value": f"{pct}% of plan",
                "hint": (f"{budget['label']} through {ytd['through_label']}; {elapsed}% of the year elapsed; "
                         f"revenue {_m(gf_ytd['revenue_actual'])} received so far"),
            })
    return stats, charts


# Known one-off events worth marking on the all-funds series. Keep this list
# short and factual; each entry is checked against the ledger before it is added.
HISTORY_MARKERS = [
    {"x": "FY2018", "label": "Water and sewer capital contributions recorded (accounting entry, not cash spending)"},
]


def build_history_charts(budget: dict) -> list:
    history = budget.get("history")
    if not history:
        return []
    def fy(row: dict) -> str:
        return f"FY{row['fiscal_year_end']}"
    def m(v: int) -> float:
        return round(v / 1e6, 2)
    first, last = fy(history[0]), fy(history[-1])
    gf_rev = {"label": "Amended budget", "points": [{"x": fy(r), "y": m(r["general_fund"]["revenue_amended"])} for r in history]}
    gf_rev_a = {"label": "Actual", "points": [{"x": fy(r), "y": m(r["general_fund"]["revenue_actual"])} for r in history]}
    gf_exp = {"label": "Amended budget", "points": [{"x": fy(r), "y": m(r["general_fund"]["expenditure_amended"])} for r in history]}
    gf_exp_a = {"label": "Actual", "points": [{"x": fy(r), "y": m(r["general_fund"]["expenditure_actual"])} for r in history]}
    all_rev = {"label": "Revenue", "points": [{"x": fy(r), "y": m(r["all_funds"]["revenue_actual"])} for r in history]}
    all_exp = {"label": "Spending", "points": [{"x": fy(r), "y": m(r["all_funds"]["expenditure_actual"])} for r in history]}
    span = f"{first}–{last}"
    xs = {fy(r) for r in history}
    markers = [mk for mk in HISTORY_MARKERS if mk["x"] in xs]
    charts = [
        {"type": "trend", "title": f"General Fund spending: amended budget vs actual, {span} ($M)",
         "unit": "$M", "lines": [gf_exp, gf_exp_a]},
        {"type": "trend", "title": f"General Fund revenue: amended budget vs actual, {span} ($M)",
         "unit": "$M", "lines": [gf_rev, gf_rev_a]},
        {"type": "trend", "title": f"All City funds: revenue and spending by year, {span} ($M)",
         "unit": "$M", "lines": [all_rev, all_exp], **({"markers": markers} if markers else {})},
    ]
    return charts


SOURCE_GROUPS = [
    ("taxes", "Property taxes"),
    ("state", "State shared revenue and grants"),
    ("federal", "Federal grants"),
    ("charges", "Charges for services"),
    ("licenses_permits", "Licenses, permits and franchise fees"),
    ("interest", "Interest"),
    ("other", "Other"),
    ("transfers_in", "Transfers in"),
    ("fines", "Fines"),
    ("local_units", "Local contributions"),
    ("unclassified", "Unclassified"),
]
DEPT_LINES = 6   # departments shown as separate lines; the rest fold into "all other"


def _source_rows(budget: dict, scope: str) -> list:
    return sorted((r for r in budget.get("revenue_sources", []) if r.get("scope") == scope),
                  key=lambda r: r["fiscal_year_end"])


def build_revenue_source_chart(budget: dict, scope: str, label: str) -> dict | None:
    rows = _source_rows(budget, scope)
    if not rows:
        return None
    latest = rows[-1]
    series = [{"label": name, "value": round(latest[key] / 1e6, 2)} for key, name in SOURCE_GROUPS
              if latest.get(key, 0) > 0]
    return {"type": "bars", "title": f"Revenue by source, {label}, FY{latest['fiscal_year_end']} ($M, City ledger)",
            "unit": "$M", "series": series}


def build_revenue_source_trend(budget: dict) -> dict | None:
    rows = _source_rows(budget, "general_fund")
    if len(rows) < 2:
        return None
    keys = ["taxes", "state", "charges", "licenses_permits", "federal"]
    names = dict(SOURCE_GROUPS)
    lines = [{"label": names[k], "points": [{"x": f"FY{r['fiscal_year_end']}", "y": round(r[k] / 1e6, 2)} for r in rows]}
             for k in keys]
    span = f"FY{rows[0]['fiscal_year_end']}–FY{rows[-1]['fiscal_year_end']}"
    return {"type": "trend", "title": f"General Fund revenue by source, {span} ($M)", "unit": "$M", "lines": lines,
            "markers": [{"x": "FY2022", "label": "American Rescue Plan funds"}] if any(r["fiscal_year_end"] == 2022 for r in rows) else []}


def build_department_trend(budget: dict) -> dict | None:
    rows = budget.get("department_history") or []
    if not rows:
        return None
    years = sorted({r["fiscal_year_end"] for r in rows})
    totals: dict[str, int] = {}
    names: dict[str, str] = {}
    for r in rows:
        code = r["code"]
        totals[code] = totals.get(code, 0) + r["amount"]
        if r.get("name"):
            names[code] = r["name"]
    names["999"] = "Transfers to other funds"
    top = [c for c, _ in sorted(totals.items(), key=lambda kv: kv[1], reverse=True) if c in names][:DEPT_LINES]
    by_year: dict[tuple, int] = {}
    for r in rows:
        by_year[(r["fiscal_year_end"], r["code"])] = by_year.get((r["fiscal_year_end"], r["code"]), 0) + r["amount"]
    lines = []
    for code in top:
        lines.append({"label": _title(names[code]) if code != "999" else names[code],
                      "points": [{"x": f"FY{y}", "y": round(by_year.get((y, code), 0) / 1e6, 2)} for y in years]})
    other_pts = []
    for y in years:
        other = sum(v for (yy, c), v in by_year.items() if yy == y and c not in top)
        other_pts.append({"x": f"FY{y}", "y": round(max(other, 0) / 1e6, 2)})
    lines.append({"label": "All other departments", "points": other_pts})
    span = f"FY{years[0]}–FY{years[-1]}"
    return {"type": "trend", "title": f"General Fund spending by department, {span} ($M)", "unit": "$M", "lines": lines}


def build_history_panel(budget: dict, taxroll: dict | None, audited_trends: list, latest_audited: int | None) -> dict:
    """The 'City Finances over Time' dashboard: everything multi-year, City ledger first."""
    charts = list(build_history_charts(budget))
    src_trend = build_revenue_source_trend(budget)
    if src_trend:
        charts.append(src_trend)
    dept_trend = build_department_trend(budget)
    if dept_trend:
        charts.append(dept_trend)
    if taxroll:
        _, tax_charts = build_taxable_value(taxroll)
        charts.extend(c for c in tax_charts if c["type"] == "trend")
    charts.extend(audited_trends)
    history = budget.get("history") or []
    first = history[0]["fiscal_year_end"] if history else None
    last = history[-1]["fiscal_year_end"] if history else None
    stats = []
    if history:
        gf_first, gf_last = history[0]["general_fund"], history[-1]["general_fund"]
        stats.append({"label": f"General Fund spending, FY{first} to FY{last}",
                      "value": f"{_m(gf_first['expenditure_actual'])} to {_m(gf_last['expenditure_actual'])}",
                      "hint": "actual, nominal dollars, City ledger"})
        all_first, all_last = history[0]["all_funds"], history[-1]["all_funds"]
        stats.append({"label": f"All-funds spending, FY{first} to FY{last}",
                      "value": f"{_m(all_first['expenditure_actual'])} to {_m(all_last['expenditure_actual'])}",
                      "hint": "actual, all City funds including water and sewer"})
        surplus_years = sum(1 for r in history if r["general_fund"]["revenue_actual"] >= r["general_fund"]["expenditure_actual"])
        stats.append({"label": "Years the General Fund ended in surplus",
                      "value": f"{surplus_years} of {len(history)}",
                      "hint": "revenue at or above spending, FY%d to FY%d" % (first, last)})
    yr = f"FY{latest_audited}" if latest_audited else "latest"
    return {
        "title": "City Finances over Time",
        "subtitle": f"FY{first} to FY{last} from the City General Ledger, with State-audited trends",
        "stats": stats,
        "charts": charts,
        "source": (f"City of Burton General Ledger (BS&A), posted activity by fiscal year FY{first} to FY{last} "
                   f"(aggregates extracted {budget['extracted']}); City Assessor (BS&A Assessing) for taxable value; "
                   f"State of Michigan Community Financials (audited F-65) for the audited trends through {yr}."),
        "links": [
            {"text": "City Finances (current plan)", "href": "#finances"},
            {"text": "Michigan Community Financials dashboard",
             "href": f"https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/{ENTITY_ID}"},
        ],
        "notes": [
            "Ledger series are unaudited posted activity by fiscal year (July to June) in nominal dollars; the General "
            "Fund figures match the State-reported audited totals in every overlapping year to within rounding.",
            "FY2018 all-funds spending includes a bookkeeping entry recording water and sewer system assets, not cash "
            "paid out. FY2022 General Fund revenue includes $3.0 million of one-time American Rescue Plan funds. "
            "City Hall department spending includes retiree and legacy costs from FY2016 onward.",
            "Revenue groups follow the Michigan uniform chart of accounts ranges (taxes, licenses and permits, "
            "federal, state, charges for services, fines, interest, other, transfers in).",
        ],
    }


def build_taxable_value(taxroll: dict) -> tuple[list, list]:
    tv = taxroll["taxable_value"]
    year = tv["year"]
    stats = [{"label": "Taxable value", "value": _m(tv["total"]),
              "hint": f"{year} assessment roll, City Assessor (BS&A)"}]
    charts = [
        {"type": "trend", "title": "Taxable value by year, City assessment rolls ($M)", "unit": "$M",
         "points": [{"x": str(h["year"]), "y": round(h["taxable"] / 1e6, 1)} for h in tv["history"]]},
        {"type": "donut", "title": f"Taxable value by property class, {year}", "unit": "$M",
         "series": [{"label": g["group"], "value": round(g["taxable"] / 1e6, 1)} for g in tv["by_group"]
                    if g["taxable"] > 0]},
    ]
    return stats, charts


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


STREET_FUNDS = {"202", "203", "451"}
UTILITY_FUNDS = {"590", "591"}


def classify_spend(fund: str, obj: str) -> str:
    """Reference copy of Get-SpendCategory in Export-BsaSpend.ps1"""
    o = int(obj)
    if fund == "703":
        return "passthrough"
    if fund == "591" and o == 816:
        return "water_purchase"
    if fund == "590" and o == 928:
        return "sewage_treatment"
    if fund == "226" and o == 830:
        return "trash"
    if fund in STREET_FUNDS and (o in (802, 818, 988) or (970 <= o <= 989)):
        return "streets"
    if fund in UTILITY_FUNDS and o in (58, 132, 136, 158, 562, 582, 971, 975, 977, 985):
        return "utility_projects"
    if fund in UTILITY_FUNDS and o == 300:
        return "debt"
    if o in (950, 952, 991, 993, 994, 999):
        return "debt"
    if o in (123, 231, 237, 238, 239, 719, 831, 874, 875):
        return "insurance_benefits"
    if 920 <= o <= 929:
        return "utilities"
    if o in (101, 140, 146, 148, 571, 850, 863, 867, 868, 934, 974, 983) or (970 <= o <= 989):
        return "vehicles_equipment"
    if 800 <= o <= 899:
        return "services"
    if 700 <= o <= 799:
        return "supplies"
    if 900 <= o <= 969:
        return "other_operations"
    if o < 400 or (600 <= o <= 699):
        return "refunds_deposits"
    return "other"


def load_spend_file(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_spend(raw, path)


def validate_spend(data: Any, where: str = "spend file") -> dict:
    if not isinstance(data, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "latest_complete_fy", "category_labels", "by_fiscal_year", "cells"):
        if key not in data:
            sys.exit(f"{where}: missing '{key}'")
    if not isinstance(data["extracted"], str) or len(data["extracted"]) != 10:
        sys.exit(f"{where}: 'extracted' must be a 10-character date string")
    if not isinstance(data["latest_complete_fy"], int):
        sys.exit(f"{where}: 'latest_complete_fy' must be an integer")
    labels = data["category_labels"]
    if not isinstance(labels, dict) or len(labels) < 10 or not all(isinstance(k, str) for k in labels):
        sys.exit(f"{where}: 'category_labels' must have at least 10 string keys")
    if "passthrough" not in labels or "other" not in labels:
        sys.exit(f"{where}: category_labels must include 'passthrough' and 'other'")
    rows = data["by_fiscal_year"]
    if not isinstance(rows, list) or not rows:
        sys.exit(f"{where}: 'by_fiscal_year' must be a non-empty list")
    cat_keys = set(labels.keys()) - {"passthrough"}
    years = []
    complete_years = []
    for row in rows:
        fy = row.get("fiscal_year")
        if not isinstance(fy, int):
            sys.exit(f"{where}: by_fiscal_year row missing integer fiscal_year")
        years.append(fy)
        if row.get("complete") is True:
            complete_years.append(fy)
        if not isinstance(row.get("invoices"), int):
            sys.exit(f"{where}: FY{fy} invoices must be an integer")
        for key in ("invoice_total", "distribution_total", "passthrough", "city_total"):
            if not isinstance(row.get(key), int) or row[key] < 0:
                sys.exit(f"{where}: FY{fy} {key} must be a non-negative integer")
        if not isinstance(row.get("payees"), int) or row["payees"] < 1:
            sys.exit(f"{where}: FY{fy} payees must be an integer >= 1")
        top10 = row.get("top10_share")
        if not isinstance(top10, (int, float)) or not (0 <= top10 <= 1):
            sys.exit(f"{where}: FY{fy} top10_share must be a float between 0 and 1")
        cats = row.get("categories")
        if not isinstance(cats, dict) or set(cats.keys()) != cat_keys:
            sys.exit(f"{where}: FY{fy} categories keys must match category_labels minus 'passthrough'")
        for k, v in cats.items():
            if not isinstance(v, int) or v < 0:
                sys.exit(f"{where}: FY{fy} categories.{k} must be a non-negative integer")
        # Tolerance of 5, not 2: the exporter rounds each of the ~14 categories to a
        # whole dollar independently, which can drift the sum a few dollars from the
        # separately-rounded city_total (observed up to 3 in the real FY2016 data).
        # Each category is rounded to whole dollars separately from city_total, so the
        # sums can drift by up to half a dollar per category.
        if abs(sum(cats.values()) - row["city_total"]) > len(cats):
            sys.exit(f"{where}: FY{fy} categories do not sum to city_total")
        groups = row.get("fund_groups")
        if not isinstance(groups, dict):
            sys.exit(f"{where}: FY{fy} fund_groups must be an object")
        for k, v in groups.items():
            if not isinstance(v, int) or v < 0:
                sys.exit(f"{where}: FY{fy} fund_groups.{k} must be a non-negative integer")
        if abs(sum(groups.values()) - row["city_total"]) > max(len(groups), 5):
            sys.exit(f"{where}: FY{fy} fund_groups do not sum to city_total")
        if row.get("complete") is True:
            if not (2000 <= row["invoices"] <= 20000):
                sys.exit(f"{where}: FY{fy} invoices out of plausible range")
            if not (10_000_000 <= row["city_total"] <= 150_000_000):
                sys.exit(f"{where}: FY{fy} city_total out of plausible range")
    if years != sorted(set(years)):
        sys.exit(f"{where}: by_fiscal_year years must be ascending and unique")
    if len(complete_years) < 8:
        sys.exit(f"{where}: fewer than 8 complete fiscal years")
    if data["latest_complete_fy"] not in complete_years:
        sys.exit(f"{where}: latest_complete_fy is not among the complete years")
    for cell in data["cells"]:
        fund, obj, cat = cell.get("fund"), cell.get("object"), cell.get("category")
        if classify_spend(fund, obj) != cat:
            sys.exit(f"{where}: cell {fund}-{obj} classifies as {classify_spend(fund, obj)!r}, not {cat!r}")
    return data


def build_spend(spend: dict) -> tuple[list, list]:
    labels = spend["category_labels"]
    rows = spend["by_fiscal_year"]
    fy = spend["latest_complete_fy"]
    last = next(r for r in rows if r["fiscal_year"] == fy)
    complete = sorted((r for r in rows if r["complete"]), key=lambda r: r["fiscal_year"])

    top_key = max((k for k in last["categories"] if k != "other"), key=lambda k: last["categories"][k])
    top_amount = last["categories"][top_key]
    top_pct = round(100 * top_amount / last["city_total"]) if last["city_total"] else 0

    stats = [
        {"label": "Paid to vendors last fiscal year", "value": _m(last["city_total"]),
         "hint": (f"FY{fy}, July {fy - 1} to June {fy}: {last['invoices']:,} invoices to {last['payees']:,} payees "
                  f"through Accounts Payable; wages and benefits paid through payroll are not included")},
        {"label": "Collected for other governments", "value": _m(last["passthrough"]),
         "hint": (f"FY{fy}: property taxes the Treasurer collected and passed on to the schools, Genesee County "
                  f"and the State; not City spending")},
        {"label": "Largest spending category", "value": labels[top_key],
         "hint": f"FY{fy}: {_m(top_amount)}, {top_pct}% of vendor payments"},
        {"label": "Paid to the ten largest payees", "value": f"{round(100 * last['top10_share'])}%",
         "hint": f"share of FY{fy} vendor payments; no payee is named on this site"},
    ]

    def _bars(amounts: dict[str, int], title: str) -> dict:
        series = []
        for key, amt in sorted(amounts.items(), key=lambda kv: kv[1], reverse=True):
            val = round(amt / 1e6, 2)
            if val == 0.0:
                continue
            series.append({"label": labels.get(key, key), "value": val})
        return {"type": "bars", "title": title, "unit": "$M", "series": series}

    cat_chart = _bars(last["categories"], f"What the City bought, FY{fy} ($M)")
    # fund_groups keys are already display names, not category keys
    fund_series = []
    for key, amt in sorted(last["fund_groups"].items(), key=lambda kv: kv[1], reverse=True):
        val = round(amt / 1e6, 2)
        if val == 0.0:
            continue
        fund_series.append({"label": key, "value": val})
    fund_chart = {"type": "bars", "title": f"Vendor payments by fund, FY{fy} ($M)", "unit": "$M", "series": fund_series}

    first_complete = complete[0]["fiscal_year"]
    trend = {
        "type": "trend",
        "title": f"Vendor payments by year, FY{first_complete} to FY{fy} ($M)",
        "unit": "$M",
        "lines": [
            {"label": "City spending",
             "points": [{"x": f"FY{r['fiscal_year']}", "y": round(r["city_total"] / 1e6, 2)} for r in complete]},
            {"label": "Passed through to other governments",
             "points": [{"x": f"FY{r['fiscal_year']}", "y": round(r["passthrough"] / 1e6, 2)} for r in complete]},
        ],
    }

    charts = [cat_chart, trend, fund_chart]
    return stats, charts


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


def reuse_audited(existing_path: str, existing_history_path: str) -> tuple[list, list, int | None]:
    """Offline mode: keep the committed audited stats and trend charts untouched
    when the State API is unreachable, so a GL refresh never erases them.

    The health stats live in the Finances panel (existing_path); the audited
    trend charts live in the History panel (existing_history_path) -- see
    build_history_panel, which is the only place `trends` is ever written."""
    with open(existing_path, encoding="utf-8") as fh:
        panel = json.load(fh)
    with open(existing_history_path, encoding="utf-8") as fh:
        history_panel = json.load(fh)
    health = [st for st in panel.get("stats", []) if st.get("label") in AUDITED_STAT_LABELS]
    trends = [c for c in history_panel.get("charts", []) if c.get("type") == "trend" and "audited" in c.get("title", "")]
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
    ap.add_argument("--taxroll-file", default=TAXROLL_FILE if os.path.exists(TAXROLL_FILE) else None,
                    help="Tax/Assessing aggregate export from tools/Export-BsaTaxRoll.ps1 "
                         "(default: tools/data/bsa-taxroll.json when present)")
    ap.add_argument("--offline", action="store_true",
                    help="reuse the audited stats and trends already in public/info-finances.json "
                         "instead of calling the State API")
    args = ap.parse_args()

    budget = load_budget_file(args.budget_file)
    spend = load_spend_file(SPEND_FILE)
    if args.offline:
        health, trends, latest_year = reuse_audited(OUT, OUT_HISTORY)
    else:
        snapshot = fetch_snapshot()
        analytics = fetch_analytics()
        trends, latest_year = build_trends(snapshot)
        health = build_health_stats(snapshot, analytics, latest_year)
    budget_stats = build_budget_stats(budget)
    budget_charts = build_budget_charts(budget)
    actual_stats, actual_charts = build_actuals(budget)
    spend_stats, spend_charts = build_spend(spend)
    taxroll = load_taxroll_file(args.taxroll_file) if args.taxroll_file else None
    tax_stats, tax_charts = build_taxable_value(taxroll) if taxroll else ([], [])
    tax_donuts = [c for c in tax_charts if c["type"] != "trend"]
    gl_revenue_chart = build_revenue_source_chart(budget, "governmental", "governmental funds")
    history_panel = build_history_panel(budget, taxroll, trends, latest_year)

    revenue_chart = gl_revenue_chart or {
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
        "stats": budget_stats + tax_stats + CITY_STATS + actual_stats + spend_stats + health,
        "charts": [revenue_chart] + budget_charts + actual_charts + spend_charts + tax_donuts,
        "source": (
            f"City of Burton General Ledger (BS&A) for the {budget['label']} adopted-budget figures "
            f"(aggregates extracted {budget['extracted']}) and for budget-vs-actual comparisons; City Assessor "
            "(BS&A Assessing) for taxable value; City of Burton " + BUDGET_YEAR + " Approved Budget (Controller's "
            "Office) for staffing; State of Michigan Community Financials (audited F-65 actuals) for the "
            "historical trends."
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
            "Budget-vs-actual figures compare the amended budget with activity posted in the City's General "
            "Ledger through fiscal year end (June 30); they are unaudited and can differ slightly from the "
            "audited statements. Year-to-date figures cover completed months only.",
            "The multi-year ledger series start with FY2008, the first full year in the current ledger. The "
            "General Fund figures match the State-reported audited totals in every overlapping year to within "
            "rounding. All-funds spending includes enterprise funds (water and sewer) and one-off items such as "
            "bond proceeds paid out, so single-year jumps are usually financing events, not operations.",
            "Taxable value is the March Board of Review value on each year's assessment roll; the current "
            "year's roll can still change with appeals and corrections.",
            "Audited trends and fiscal-health figures come from the State of Michigan Community Financials "
            "program (audited F-65 annual financial reports).",
            "Vendor payments come from the City's Accounts Payable records and cover invoices paid, not payroll. "
            "Property taxes collected for the schools, the County and the State pass through the City's books and "
            "are shown separately, never as City spending. Categories group the ledger's object codes; no vendor "
            "is named.",
        ],
    }

    write_json(OUT, panel)
    write_json(OUT_HISTORY, history_panel)
    print(f"Wrote {OUT}")
    print(f"Wrote {OUT_HISTORY}  ({len(history_panel['charts'])} charts)")
    print(f"  latest audited year: {latest_year}")
    print(f"  stats: {len(panel['stats'])}  charts: {len(panel['charts'])} ({len(trends)} state trends)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
