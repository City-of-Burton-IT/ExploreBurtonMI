# Build public/info-utilities.json for the "Water & Sewer Funds" dashboard.
#
# Sources (City records, aggregates only):
#   * tools/data/bsa-budget.json `enterprise_funds`: Water (591) and Sewer (590)
#     fund revenue and spending by fiscal year in resident-facing groups, from
#     the General Ledger (tools/Export-BsaBudget.ps1).
#   * tools/data/bsa-residential.json `utility`: typical bills and customer
#     counts from Utility Billing (tools/Export-BsaCostOfLiving.ps1).
#
# Framing: the two funds are enterprise funds. Bills, not taxes, pay for them;
# the chart answers "what does my water and sewer money buy".
#
#   python tools/build_utilities.py
from __future__ import annotations

import json
import os
import sys

from lib.iox import write_json
from lib.paths import public_path

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_FILE = os.path.join(HERE, "data", "bsa-budget.json")
RESIDENTIAL_FILE = os.path.join(HERE, "data", "bsa-residential.json")
OUT = public_path("info-utilities.json")

FUND_NAMES = {"591": "Water", "590": "Sewer"}
SPEND_GROUPS = [
    ("treatment_purchase", "Purchased water and sewage treatment"),
    ("operations", "Operations"),
    ("depreciation", "Depreciation"),
    ("debt_and_transfers", "Debt interest and transfers"),
]
# Short, fund-specific legend labels for the donuts (legend space is narrow).
DONUT_LABELS = {
    "591": {"treatment_purchase": "Purchased water", "operations": "Operations", "depreciation": "Depreciation", "debt_and_transfers": "Debt and transfers"},
    "590": {"treatment_purchase": "Sewage treatment", "operations": "Operations", "depreciation": "Depreciation", "debt_and_transfers": "Debt and transfers"},
}


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_enterprise(rows: object, where: str = "budget file") -> list:
    if not isinstance(rows, list) or len(rows) < 10:
        sys.exit(f"{where}: enterprise_funds must list at least ten fund-years")
    for r in rows:
        if r.get("fund") not in FUND_NAMES or not isinstance(r.get("fiscal_year_end"), int):
            sys.exit(f"{where}: enterprise_funds rows need fund 590/591 and an integer fiscal_year_end")
        for key in ("usage_fees", "other_revenue", "treatment_purchase", "operations", "depreciation", "debt_and_transfers"):
            if not isinstance(r.get(key), int):
                sys.exit(f"{where}: enterprise_funds {r.get('fund')} {r.get('fiscal_year_end')} {key} must be an integer")
    return rows


def _m(v: int) -> str:
    return f"${v / 1e6:.1f}M"


def _fy(year: int) -> str:
    return f"FY{year}"


def build_panel(enterprise: list, utility: dict | None, extracted: str) -> dict:
    by_fund: dict[str, list] = {"591": [], "590": []}
    for r in sorted(enterprise, key=lambda r: (r["fund"], r["fiscal_year_end"])):
        by_fund[r["fund"]].append(r)
    latest_year = max(r["fiscal_year_end"] for r in enterprise)
    latest = {f: next(r for r in rows if r["fiscal_year_end"] == latest_year) for f, rows in by_fund.items()}
    first_year = min(r["fiscal_year_end"] for r in enterprise)
    span = f"{_fy(first_year)}–{_fy(latest_year)}"

    def spend(r: dict) -> int:
        return sum(r[k] for k, _ in SPEND_GROUPS)

    def revenue(r: dict) -> int:
        return r["usage_fees"] + r["other_revenue"]

    stats = []
    for fund in ("591", "590"):
        r = latest[fund]
        share = round(100 * r["treatment_purchase"] / spend(r)) if spend(r) else 0
        stats.append({
            "label": f"{FUND_NAMES[fund]} fund: bills collected, {_fy(latest_year)}",
            "value": _m(r["usage_fees"]),
            "hint": f"usage fees; spending {_m(spend(r))}, of which {share}% was "
                    + ("purchased water" if fund == "591" else "sewage treatment"),
        })
    if utility:
        stats.append({
            "label": "Customer accounts",
            "value": f"{utility['customers_residential']:,}",
            "hint": f"active residential accounts; {utility['customers_commercial']:,} commercial. "
                    f"About {utility['accounts_sewer_only']:,} homes are sewer-only (private wells).",
        })
        stats.append({
            "label": "Typical water and sewer bill",
            "value": f"${utility['median_annual_water_sewer']:,}/yr",
            "hint": f"median for homes on City water and sewer; sewer-only homes ${utility['median_annual_sewer_only']:,}/yr",
        })

    charts = []
    for fund in ("591", "590"):
        rows = by_fund[fund]
        name = FUND_NAMES[fund]
        charts.append({
            "type": "trend", "title": f"{name} fund: revenue and spending by year, {span} ($M)", "unit": "$M",
            "lines": [
                {"label": "Revenue (bills and other)", "points": [{"x": _fy(r["fiscal_year_end"]), "y": round(revenue(r) / 1e6, 2)} for r in rows]},
                {"label": "Spending", "points": [{"x": _fy(r["fiscal_year_end"]), "y": round(spend(r) / 1e6, 2)} for r in rows]},
            ],
        })
    for fund in ("591", "590"):
        r = latest[fund]
        charts.append({
            "type": "donut", "title": f"Where the {FUND_NAMES[fund].lower()} dollar went, {_fy(latest_year)}", "unit": "$M",
            "series": [{"label": DONUT_LABELS[fund][key], "value": round(r[key] / 1e6, 2)} for key, _ in SPEND_GROUPS if r[key] > 0],
        })
    charts.append({
        "type": "trend", "title": f"Cost of purchased water and sewage treatment by year, {span} ($M)", "unit": "$M",
        "lines": [
            {"label": "Purchased water (Water fund)", "points": [{"x": _fy(r["fiscal_year_end"]), "y": round(r["treatment_purchase"] / 1e6, 2)} for r in by_fund["591"]]},
            {"label": "Sewage treatment (Sewer fund)", "points": [{"x": _fy(r["fiscal_year_end"]), "y": round(r["treatment_purchase"] / 1e6, 2)} for r in by_fund["590"]]},
        ],
    })

    explainer = {
        "title": "How to read these numbers",
        "intro": "Water and sewer are run as separate businesses inside the City: your bill is their income.",
        "items": [
            {"term": "Enterprise funds",
             "body": "The Water and Sewer funds take in bill payments and pay their own costs. Property taxes do "
                     "not fund them, and their money is not used for police, roads or City Hall."},
            {"term": "Purchased water and treatment",
             "body": "Burton buys treated drinking water from the regional system and pays Genesee County to "
                     "treat its sewage. Those wholesale charges are the largest cost in each fund and the "
                     "part the City controls least."},
            {"term": "Depreciation",
             "body": "An accounting charge that spreads the cost of pipes, pumps and plant over their useful "
                     "life. It is not cash paid out in the year, but it shows how much of the system is "
                     "wearing out and will need replacing."},
            {"term": "Revenue above spending",
             "body": "When bills collected exceed spending, the difference builds reserves for main "
                     "replacements and debt payments, and covers years when a major repair hits."},
        ],
    }

    return {
        "title": "Water & Sewer Funds",
        "subtitle": f"What water and sewer bills pay for, {span}, from the City General Ledger",
        "stats": stats,
        "charts": charts,
        "explainer": explainer,
        "source": (f"City of Burton General Ledger (BS&A), Water (591) and Sewer (590) enterprise funds, posted activity "
                   f"through {_fy(latest_year)} (aggregates extracted {extracted})"
                   + ("; City of Burton Utility Billing (BS&A) for customer counts and typical bills." if utility else ".")),
        "links": [
            {"text": "What It Costs to Live Here", "href": "#costofliving"},
            {"text": "Drinking Water (EPA compliance)", "href": "#water"},
            {"text": "City Finances", "href": "#finances"},
        ],
        "notes": [
            "Figures are posted ledger activity by fiscal year (July to June), unaudited; the audited statements "
            "can differ slightly. Revenue includes usage fees plus interest and other income. Spending groups "
            "follow the City's chart of accounts: purchased water and treatment, operations, depreciation, and "
            "debt interest and transfers.",
            "Only fund-level aggregates are published, never individual accounts or bills.",
        ],
    }


def main() -> int:
    budget = load_json(BUDGET_FILE)
    enterprise = validate_enterprise(budget.get("enterprise_funds"), BUDGET_FILE)
    utility = None
    if os.path.exists(RESIDENTIAL_FILE):
        util = load_json(RESIDENTIAL_FILE).get("utility")
        if util and all(isinstance(util.get(k), int) and util[k] > 0 for k in
                        ("customers_residential", "customers_commercial", "accounts_sewer_only",
                         "median_annual_water_sewer", "median_annual_sewer_only")):
            utility = util
    panel = build_panel(enterprise, utility, budget["extracted"])
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    for s in panel["stats"]:
        print(f"  {s['label']}: {s['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
