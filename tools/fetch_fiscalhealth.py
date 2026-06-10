"""Build public/info-fiscalhealth.json: a City Fiscal Health dashboard.

This is the resident-facing "is the city financially sustainable, and what does
that mean for my household" view. It is deliberately NET-NEW relative to the
Finances dashboard (which shows the adopted budget mix and raw multi-year dollar
trends). Fiscal Health re-frames the same audited figures the way a resident
actually feels them:

  * PER-RESIDENT obligations (long-term debt and unfunded pension divided by
    population) -- a number a household can relate to, which Finances never shows.
  * A sustainability RATIO (debt as a share of the city's taxable value).
  * Burton's STATEWIDE RANK across fiscal-health measures (cash on hand, general-
    fund reserves, net financial position), drawn as percentiles so "healthier
    than X% of Michigan cities" reads at a glance. Finances shows only one rank
    as a single stat; the ranked comparison is the centerpiece here.

Source: State of Michigan Community Financials program (the same audited F-65
data behind micommunityfinancials.michigan.gov). Population is the U.S. Census
2020 count, matching the Demographics dashboard so per-resident figures are
consistent across the site.

Rank direction (verified against the live API, 2026-06): rank 1 = healthiest.
A wealthy city (Troy) ranks worse on cash-on-hand than Burton because rank
follows the metric value (higher value -> lower/better rank number). Percentile
"healthier than X%" = (total - rank) / total.

Re-runnable (committed output; the site reads the JSON, never the API):
    python tools/fetch_fiscalhealth.py

Stdlib only (urllib), matching the other tools/ scripts.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any, cast

ENTITY_ID = "2612060"  # Burton city (Census GEOID; confirmed against the API)
API = "https://micommunityfinancials.michigan.gov/api/component"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-fiscalhealth.json"))

# Population used for per-resident figures. U.S. Census 2020; matches the
# Demographics dashboard so the same denominator is used everywhere on the site.
POPULATION = 29_529

# Statewide-rank measures to chart (analytics key -> resident-friendly label).
# Each is "higher value = healthier = lower rank number"; we render a percentile.
RANK_MEASURES = [
    ("general_fund_cash_Ratio", "Cash on hand"),
    ("general_fund_ratio", "General Fund reserves"),
    ("governmental_net_position_ratio", "Net financial position"),
]


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def fetch_snapshot() -> dict:
    return cast(dict, _get(f"{API}/snapshot.json?component_index=3&entity_id={ENTITY_ID}&filter_type=CITY"))


def fetch_analytics() -> list:
    return cast(list, _get(f"{API}/analytics.json?component_index=4&entity_id={ENTITY_ID}&filter_type=CITY&year=2025"))


def _latest(snapshot: dict, name: str):
    """Latest non-null value for a snapshot dimension, with its year."""
    years = snapshot.get("years", [])
    for item in snapshot.get("data", []):
        if item.get("dimension", {}).get("name") == name:
            vals = item.get("values", [])
            for i in range(len(vals) - 1, -1, -1):
                if vals[i] is not None:
                    yr = years[i] if i < len(years) else None
                    return vals[i], yr
    return None, None


def _rank_index(analytics: list) -> dict:
    return {a.get("key_entity"): a for a in analytics}


def _percentile(rank: float, total: float) -> int:
    """Share of cities Burton is healthier than. Rank 1 = healthiest."""
    return round((total - rank) / total * 100)


def main() -> int:
    snapshot = fetch_snapshot()
    analytics = fetch_analytics()
    idx = _rank_index(analytics)

    debt, debt_yr = _latest(snapshot, "Long Term Debt")
    pension, _ = _latest(snapshot, "Unfunded Pension Liability")
    tv, _ = _latest(snapshot, "Total Taxable Value")
    if debt is None or pension is None or tv is None:
        raise SystemExit("Missing debt / pension / taxable-value figures from the API.")

    yr = f"audited FY{debt_yr}" if debt_yr else "audited"
    debt_per = round(debt / POPULATION)
    pension_per = round(pension / POPULATION)
    debt_pct_tv = debt / tv * 100

    reserve = idx.get("general_fund_ratio", {})
    reserve_rank = int(reserve["rank"]) if reserve.get("rank") else None
    reserve_total = int(reserve["total"]) if reserve.get("total") else None

    stats = [
        {"label": "Long-term debt per resident", "value": f"${debt_per:,}",
         "hint": f"${debt / 1e6:.1f}M / {POPULATION:,} residents ({yr})"},
        {"label": "Pension owed per resident", "value": f"${pension_per:,}",
         "hint": f"${pension / 1e6:.1f}M unfunded / residents ({yr})"},
        {"label": "Debt vs. property value", "value": f"{debt_pct_tv:.1f}%",
         "hint": "long-term debt as a share of the city's taxable value"},
    ]
    if reserve_rank and reserve_total:
        stats.append({
            "label": "Reserve rank in Michigan",
            "value": f"{reserve_rank} of {reserve_total}",
            "hint": "general-fund reserves; 1 = healthiest city",
        })

    # Centerpiece: statewide percentile across fiscal-health measures.
    rank_series = []
    pct_lookup: dict[str, int] = {}
    for key, label in RANK_MEASURES:
        a = idx.get(key, {})
        if a.get("rank") and a.get("total"):
            pct = _percentile(float(a["rank"]), float(a["total"]))
            pct_lookup[key] = pct
            rank_series.append({"label": label, "value": pct})

    charts = [
        {"type": "bars",
         "title": "Where Burton ranks among Michigan cities (healthier than this share)",
         "unit": "%", "series": rank_series},
        {"type": "bars", "title": "Long-term obligations per resident", "unit": "$",
         "series": [
             {"label": "Debt", "value": debt_per},
             {"label": "Unfunded pension", "value": pension_per},
         ]},
    ]

    cash_pct = pct_lookup.get("general_fund_cash_Ratio")
    reserve_pct = pct_lookup.get("general_fund_ratio")
    netpos_pct = pct_lookup.get("governmental_net_position_ratio")
    rank_sentence = ""
    if cash_pct is not None and reserve_pct is not None and netpos_pct is not None:
        rank_sentence = (
            f"Compared with other Michigan cities, Burton sits near the middle: healthier than "
            f"about {cash_pct}% of cities on cash on hand and {reserve_pct}% on general-fund "
            f"reserves, but below the middle ({netpos_pct}%) on overall net financial position. "
            "In plain terms, the city keeps a reasonable cushion for day-to-day bills, while "
            "long-term promises -- pensions and retiree health care -- are the main pressure on "
            "the budget."
        )

    summary = {
        "heading": "What this means for you",
        "body": [
            f"The City of Burton carries about ${debt_per:,} per resident in long-term debt and "
            f"${pension_per:,} per resident toward pensions already earned by current and retired "
            "employees. These are not personal bills: the city repays them over many years through "
            "utility rates, dedicated road and public-safety millages, and the regular budget -- "
            "not a charge sent to your household.",
        ],
    }
    if rank_sentence:
        summary["body"].append(rank_sentence)
    summary["body"].append(
        "Burton's pension is about 68% funded and retiree health care (OPEB) about 77% funded -- "
        "so most of those long-term promises are already paid for, with the remainder set aside "
        "over time. (See the Finances dashboard for the full budget and multi-year trends.)"
    )

    panel = {
        "title": "City Fiscal Health",
        "subtitle": "How sustainable Burton's finances are -- per resident, and ranked against Michigan cities",
        "summary": summary,
        "stats": stats,
        "charts": charts,
        "source": (
            "State of Michigan Community Financials program (audited F-65 annual financial reports). "
            f"Per-resident figures use the U.S. Census 2020 population ({POPULATION:,})."
        ),
        "links": [
            {"text": "Finances dashboard (budget + trends)", "href": "#finances"},
            {"text": "Michigan Community Financials dashboard",
             "href": f"https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/{ENTITY_ID}"},
        ],
        "notes": [
            "Statewide ranks: rank 1 is the healthiest city for that measure; the bar chart shows "
            "the share of Michigan cities Burton is healthier than. \"Cash on hand\" and reserves "
            "measure short-term financial cushion; net financial position is a longer-term measure "
            "of assets minus what is owed.",
            "These figures are AUDITED actuals reported to the State of Michigan and run about a "
            "year behind the city's current adopted budget. Per-resident amounts are the city's "
            "total obligations divided by population, not amounts billed to individual households.",
            "Revenue-by-source and a debt-by-purpose / maturity breakdown are not in the state's "
            "public dataset; those would come from the city's adopted-budget revenue schedule and "
            "annual financial report (ACFR).",
        ],
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  debt/resident ${debt_per:,}  pension/resident ${pension_per:,}  debt/TV {debt_pct_tv:.1f}%")
    print(f"  percentiles: {pct_lookup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
