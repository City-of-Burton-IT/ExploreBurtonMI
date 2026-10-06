"""Build public/info-capitalprojects.json: the Capital Projects dashboard.

Shows the City of Burton's ADOPTED capital plan -- the big one-time investments
that are funded -- grouped by category and by how they are paid for. Source is a
curated CSV (pipeline/data/capital-projects.csv), one row per project-per-fiscal-
year, transcribed from the adopted budget book's capital sections + the Capital
Asset Requests sheet.

This is the adopted PLAN, not actual expenditures (honesty per ADR-0001).

Re-runnable (committed output; the site reads the JSON):
    python tools/build_capitalprojects.py

Uses the shared tools/lib helpers (repo paths, atomic writes).
"""
from __future__ import annotations

import csv
import json
import os
import sys

from lib.iox import write_json
from lib.paths import pipeline_data_path, public_path

CSV_IN = pipeline_data_path("capital-projects.csv")
OUT = public_path("info-capital.json")
BUDGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bsa-budget.json")

VALID_CATEGORIES = {
    "Major Streets", "Local Streets", "Water & Sewer", "Parks & Recreation",
    "Public Safety", "Facilities & Equipment", "Other",
}
VALID_FUNDING = {
    "Act 51", "Special Assessment", "General Fund", "Grant", "Bond",
    "Water/Sewer Revenue", "Other",
}
VALID_STATUS = {"Planned", "In progress", "Completed"}

CATEGORY_COLORS = {
    "Major Streets": "#2c57a0",
    "Local Streets": "#5c6bc0",
    "Water & Sewer": "#00897b",
    "Parks & Recreation": "#43a047",
    "Public Safety": "#c0392b",
    "Facilities & Equipment": "#e08a00",
    "Other": "#8d6e63",
}
FUNDING_COLORS = {
    "Act 51": "#2c57a0",
    "Special Assessment": "#5c6bc0",
    "General Fund": "#00897b",
    "Grant": "#e08a00",
    "Bond": "#c0392b",
    "Water/Sewer Revenue": "#7e57c2",
    "Other": "#8d6e63",
}

# City population (2020 Census / ACS), for a per-resident scale figure.
POPULATION = 29_529

# Road & street capital by fiscal year (Major + Local Streets construction totals,
# dept 451, City of Burton adopted FY2026-27 budget book). FY label = year ending
# June; these reconcile to the printed fund construction totals each year.
# FY2026-27 adopted street capital (9,797,313 major + 750,000 local). The actual
# history behind it now comes from the General Ledger (tools/data/bsa-budget.json
# `capital_history`, streets column: construction, preservation and repaving
# accounts in the Major and Local Streets funds); the FY2025 ledger figure
# matched the former typed value (3,254,866) exactly.
STREET_CAPITAL_ADOPTED = (2027, 10_547_313)


def load_street_history(path: str) -> list:
    """[(fiscal_year_end, streets_actual)] from the ledger export, or [] if absent."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh).get("capital_history") or []
    out = []
    for r in rows:
        if not isinstance(r.get("fiscal_year_end"), int) or not isinstance(r.get("streets"), int):
            sys.exit(f"{path}: capital_history rows need integer fiscal_year_end and streets")
        out.append((r["fiscal_year_end"], r["streets"]))
    return sorted(out)


def street_capital_series(history: list) -> list:
    """Ledger actuals followed by the adopted year, for the trend chart."""
    series = [(y, v) for y, v in history if v > 0]
    if not series or series[-1][0] < STREET_CAPITAL_ADOPTED[0]:
        series.append(STREET_CAPITAL_ADOPTED)
    return series


def normalize_rows(raw: list) -> list:
    """Validate + bucket curated rows. Unknown category/funding/status -> safe
    defaults with no crash; amount coerced to a non-negative int."""
    out = []
    for r in raw:
        try:
            amount = int(round(float(str(r.get("amount", "0")).replace(",", "") or 0)))
        except (TypeError, ValueError):
            amount = 0
        if amount < 0:
            amount = 0
        category = (r.get("category") or "").strip()
        if category not in VALID_CATEGORIES:
            category = "Other"
        funding = (r.get("funding_source") or "").strip()
        if funding not in VALID_FUNDING:
            funding = "Other"
        status = (r.get("status") or "").strip() or "Planned"
        if status not in VALID_STATUS:
            status = "Planned"
        try:
            fy = int(str(r.get("fiscal_year", "")).strip())
        except (TypeError, ValueError):
            fy = 0
        out.append({
            "project": (r.get("project") or "").strip(),
            "category": category,
            "fund": (r.get("fund") or "").strip(),
            "funding_source": funding,
            "fiscal_year": fy,
            "amount": amount,
            "status": status,
        })
    return out


def aggregate(rows: list) -> dict:
    total = sum(r["amount"] for r in rows)

    def by(key):
        d = {}
        for r in rows:
            d[r[key]] = d.get(r[key], 0) + r["amount"]
        return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))

    years = sorted({r["fiscal_year"] for r in rows if r["fiscal_year"]})
    by_year = [(y, sum(r["amount"] for r in rows if r["fiscal_year"] == y)) for y in years]
    return {
        "total": total,
        "count": len(rows),
        "by_category": by("category"),
        "by_funding": by("funding_source"),
        "top": sorted(rows, key=lambda r: -r["amount"])[:10],
        "years": years,
        "by_year": by_year,
    }


def _fy_label(year: int) -> str:
    return f"FY{year - 1}-{str(year)[2:]}"  # 2027 -> FY2026-27 (Michigan July-June FY)


def _money(n: int) -> str:
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.0f}k"
    return f"${n:,}"


def build_panel(rows: list, street_history: list | None = None) -> dict:
    agg = aggregate(rows)
    streets = street_capital_series(street_history or [])
    street_span = f"{_fy_label(streets[0][0])} to {_fy_label(streets[-1][0])}" if len(streets) > 1 else ""
    years = agg["years"]
    multi = len(years) >= 2
    if years:
        span = _fy_label(years[0]) if not multi else f"{_fy_label(years[0])} to {_fy_label(years[-1])}"
    else:
        span = ""
    subtitle = f"Adopted capital plan, City of Burton, {span}".rstrip(", ")

    largest_cat = agg["by_category"][0][0] if agg["by_category"] else "n/a"
    per_resident = round(agg["total"] / POPULATION) if POPULATION else 0
    stats = [
        {"label": "Total capital investment", "value": _money(agg["total"]),
         "hint": "adopted plan, not money already spent"},
        {"label": "Per resident", "value": f"${per_resident:,}",
         "hint": f"across ~{POPULATION:,} residents"},
        {"label": "Funded projects", "value": str(agg["count"]),
         "hint": "across all categories"},
        {"label": "Largest category", "value": largest_cat,
         "hint": _money(agg["by_category"][0][1]) if agg["by_category"] else ""},
    ]

    charts = [
        {"type": "donut", "title": "Capital investment by category", "unit": "$",
         "series": [{"label": c, "value": v, "color": CATEGORY_COLORS.get(c, "#8d6e63")}
                    for c, v in agg["by_category"]]},
        {"type": "bars", "title": "How capital projects are funded", "unit": "$",
         "series": [{"label": f, "value": v, "color": FUNDING_COLORS.get(f, "#8d6e63")}
                    for f, v in agg["by_funding"]]},
        {"type": "bars", "title": "Largest projects", "unit": "$",
         "series": [{"label": r["project"], "value": r["amount"]} for r in agg["top"]]},
        # Multi-year context from the ledger: actual street capital by year, then
        # the adopted FY2026-27 figure as the final point.
        {"type": "trend", "title": "Road & street capital by fiscal year", "unit": "$",
         "points": [{"x": _fy_label(y), "y": v} for y, v in streets],
         "markers": [{"x": _fy_label(STREET_CAPITAL_ADOPTED[0]), "label": "Adopted plan"}]},
    ]

    table = {
        "title": "Funded capital projects",
        "columns": ["Project", "Category", "Funding", "Amount"],
        "rows": [
            {"cells": [r["project"], r["category"], r["funding_source"], _money(r["amount"])]}
            for r in sorted(rows, key=lambda r: -r["amount"])
        ],
    }

    summary = {
        "heading": "What this means for you",
        "body": [
            "Capital projects are the big one-time investments the City makes: rebuilding roads, "
            "replacing major equipment, and improving public buildings, as opposed to day-to-day "
            "operating costs. This is the adopted plan of what is funded, not money already spent.",
            f"For {span}, the largest share is road work: the City has budgeted major reconstruction "
            "on Genesee Rd, Court St, Covert Rd and others, funded mainly by state gas-tax (Act 51) "
            "dollars rather than your city property taxes. Equipment and facility investments make up "
            "the rest.",
            "This is a big road-building year: the adopted street capital of about $10.5M is well above "
            "any year in the ledger since FY2008 (the trend below shows actual street capital by year, "
            f"{street_span}). At this year's total, capital investment works out to about "
            f"${per_resident:,} per resident.",
        ],
    }

    return {
        "title": "Capital Projects",
        "subtitle": subtitle,
        "summary": summary,
        "stats": stats,
        "charts": charts,
        "tables": [table],
        "source": "City of Burton adopted FY2026-27 budget (capital sections) and Capital Asset Requests; City "
                  "General Ledger (BS&A) for actual street capital by year.",
        "links": [
            {"text": "City Finances dashboard", "href": "#finances"},
            {"text": "Roads & Pavement dashboard", "href": "#roads"},
        ],
        "notes": [
            "This is the adopted capital PLAN, not actual expenditures, and is subject to change "
            "during the year.",
            "Street projects are funded by Act 51 (state gas and weight tax) and accumulated road-fund "
            "balance, plus about $375,000 in federal/state construction aid and a $145,000 General Fund "
            "transfer in FY2026-27, not city property taxes; the CDBG paving is a federal grant. "
            "Operating costs are shown on the City Finances dashboard; this dashboard is capital only.",
            "Equipment and vehicle items are capital assets; some are prior-year approvals carried over "
            "(shown as In progress) that need no new funding this year.",
            "The street capital trend is posted spending in the Major and Local Streets funds on construction, "
            "road preservation and repaving accounts, by fiscal year, with the adopted plan as the last point; "
            "loan principal payments are not included.",
        ],
    }


def main() -> int:
    with open(CSV_IN, encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    rows = normalize_rows(raw)
    panel = build_panel(rows, load_street_history(BUDGET_FILE))
    write_json(OUT, panel)
    agg = aggregate(rows)
    print(f"Wrote {OUT}")
    print(f"  {agg['count']} projects, total {_money(agg['total'])}")
    for c, v in agg["by_category"]:
        print(f"    {v:>11,}  {c}")

    # Tie funded street projects to the Roads dashboard (table flag) and build the
    # "Funded road projects" map overlay.
    import capital_roads_link
    flagged, segs = capital_roads_link.link_all()
    print(f"  linked {flagged} road row(s) to the Roads dashboard; {segs} overlay segment(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
