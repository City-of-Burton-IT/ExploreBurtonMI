# Build public/info-permits.json for the "Building Permits" dashboard.
#
# Source (City records, aggregates only): tools/data/bsa-permits.json, written by
# tools/Export-BsaPermits.ps1 from the Assessing module's permit table.
#
# Framing: permits are the ones the City's Building Department issues and the
# Assessor records. Counts are reliable; declared value is what the applicant
# states and is often blank, so value is shown only for groups where almost
# every permit carries one.
#
#   python tools/build_permits.py
from __future__ import annotations

import json
import os
import sys

from lib.iox import write_json
from lib.paths import public_path

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "data", "bsa-permits.json")
OUT = public_path("info-permits.json")

GROUPS = ["new_homes", "home_improvements", "commercial", "demolitions", "other"]
GROUP_LABELS = {
    "new_homes": "New homes",
    "home_improvements": "Home improvements",
    "commercial": "Commercial",
    "demolitions": "Demolitions",
    "other": "Other",
}
RECENT_FROM = 2015
# A group's declared value is published only when at least this share of its
# permits stated a value.
VALUE_RELIABLE_SHARE = 0.9

NEW_HOME_CATEGORIES = {"RES, NEW CONSTRUCTION", "NEW HOUSE", "RES, MODULAR HOME"}
IMPROVEMENT_CATEGORIES = {
    "RES, ALTER/REPAIR", "RES, ADDITION", "RES, RENEWAL", "RES, FIRE REPAIR", "RES, CAR PORT",
    "ROOFING AND SIDING", "SIDING", "DECK", "POOL", "SHED", "FENCE", "POLE BARN",
    "DETACHED ACCESSORY STRUCTURE",
}


def classify_category(category: str | None) -> str:
    """Reference copy of Get-PermitGroup in Export-BsaPermits.ps1 (checked against the
    exporter's category_map at the boundary so the two cannot drift apart)."""
    c = (category or "").strip().upper()
    if c in NEW_HOME_CATEGORIES:
        return "new_homes"
    if c.startswith("DEMO"):
        return "demolitions"
    if "COMMERC" in c or c in ("CELL TOWER", "SIGN"):
        return "commercial"
    if c in IMPROVEMENT_CATEGORIES or c.startswith("GARAGE") or c.startswith("ROOF"):
        return "home_improvements"
    return "other"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _is_count(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate_permits(data: object, where: str = "permits file") -> dict:
    """Boundary check: shape errors and implausible counts stop the build."""
    if not isinstance(data, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "latest_complete_year", "permits_by_year",
                "permits_by_year_all", "time_to_complete", "category_map"):
        if key not in data:
            sys.exit(f"{where}: missing '{key}'")
    if not isinstance(data["extracted"], str) or len(data["extracted"]) != 10:
        sys.exit(f"{where}: extracted must be an ISO date")
    latest = data["latest_complete_year"]
    if not isinstance(latest, int):
        sys.exit(f"{where}: latest_complete_year must be an integer")

    all_years = data["permits_by_year_all"]
    if not isinstance(all_years, list) or len(all_years) < 20:
        sys.exit(f"{where}: permits_by_year_all must list at least 20 years")
    for r in all_years:
        if not isinstance(r, dict) or not isinstance(r.get("year"), int) or not _is_count(r.get("total")):
            sys.exit(f"{where}: permits_by_year_all rows need an integer year and total")

    rows = data["permits_by_year"]
    if not isinstance(rows, list) or not rows:
        sys.exit(f"{where}: permits_by_year must be a non-empty list")
    seen = set()
    for r in rows:
        year = r.get("year") if isinstance(r, dict) else None
        if not isinstance(year, int) or year < RECENT_FROM or year in seen:
            sys.exit(f"{where}: permits_by_year needs unique integer years from {RECENT_FROM}")
        seen.add(year)
        if not _is_count(r.get("total")) or r["total"] > 3000:
            sys.exit(f"{where}: {year} total must be an integer no higher than 3,000")
        if year <= latest and r["total"] < 200:
            sys.exit(f"{where}: {year} total {r['total']} is implausibly low for a complete year")
        for g in GROUPS:
            cell = r.get(g)
            if not isinstance(cell, dict) or not all(_is_count(cell.get(k)) for k in ("count", "value", "with_value")):
                sys.exit(f"{where}: {year} {g} needs integer count, value and with_value")
        if sum(r[g]["count"] for g in GROUPS) != r["total"]:
            sys.exit(f"{where}: {year} group counts do not add up to the total")
    if latest not in seen:
        sys.exit(f"{where}: no row for the latest complete year {latest}")
    latest_row = next(r for r in rows if r["year"] == latest)
    if not 0 <= latest_row["new_homes"]["count"] <= 300:
        sys.exit(f"{where}: {latest} new_homes {latest_row['new_homes']['count']} is outside 0 to 300")
    for year in range(RECENT_FROM, latest + 1):
        if year not in seen:
            sys.exit(f"{where}: permits_by_year is missing {year}")

    ttc = data["time_to_complete"]
    for g in ("new_homes", "home_improvements"):
        cell = ttc.get(g) if isinstance(ttc, dict) else None
        if not isinstance(cell, dict) or not _is_count(cell.get("median_days")) or not _is_count(cell.get("permits")):
            sys.exit(f"{where}: time_to_complete.{g} needs integer median_days and permits")

    for item in data["category_map"]:
        if not isinstance(item, dict) or classify_category(item.get("category")) != item.get("group"):
            sys.exit(f"{where}: category '{item.get('category') if isinstance(item, dict) else item}' "
                     f"is grouped differently by the exporter and the builder")
    return data


def _money(v: int) -> str:
    return f"${v / 1e6:.1f}M" if v >= 1_000_000 else f"${v:,}"


def reliable_value(row: dict) -> tuple[int, list[str]]:
    """Sum of declared value over the groups where nearly every permit stated one."""
    total = 0
    used = []
    for g in ("new_homes", "home_improvements", "commercial", "demolitions"):
        cell = row[g]
        if cell["count"] and cell["with_value"] / cell["count"] >= VALUE_RELIABLE_SHARE:
            total += cell["value"]
            used.append(GROUP_LABELS[g].lower())
    return total, used


def _days(n: int) -> str:
    return f"{n} days" if n < 120 else f"{round(n / 30.4)} months"


def build_panel(data: dict) -> dict:
    latest = data["latest_complete_year"]
    rows = sorted(data["permits_by_year"], key=lambda r: r["year"])
    complete = [r for r in rows if r["year"] <= latest]
    last = next(r for r in rows if r["year"] == latest)
    first_all = min(r["year"] for r in data["permits_by_year_all"] if r["year"] <= latest)
    all_complete = sorted((r for r in data["permits_by_year_all"] if r["year"] <= latest), key=lambda r: r["year"])
    ytd = data.get("year_to_date")
    ttc = data["time_to_complete"]

    stats = [
        {"label": "Permits issued last year", "value": f"{last['total']:,}",
         "hint": f"{latest}, all types: homes, roofs, fences, sheds, commercial work and demolitions"},
        {"label": "New homes permitted last year", "value": f"{last['new_homes']['count']:,}",
         "hint": f"{latest}: single-family, site-built and modular homes"},
        {"label": "Home-improvement permits last year", "value": f"{last['home_improvements']['count']:,}",
         "hint": f"{latest}: repairs, additions, roofing, siding, decks, pools, sheds and fences"},
        {"label": "Demolition permits last year", "value": f"{last['demolitions']['count']:,}",
         "hint": f"{latest}: buildings taken down"},
        {"label": "Typical time to finish a project",
         "value": _days(ttc["home_improvements"]["median_days"]),
         "hint": f"median from permit to final inspection for home improvements; new homes take about "
                 f"{_days(ttc['new_homes']['median_days'])} (permits issued since {ttc.get('since_year', 2019)} "
                 f"that have a recorded final inspection)"},
    ]
    value, used = reliable_value(last)
    if used:
        stats.append({"label": "Stated construction value last year", "value": _money(value),
                      "hint": f"{latest}: what applicants declared for {', '.join(used)} permits; "
                              f"an estimate by the applicant, not a measured cost"})
    if ytd:
        stats.append({"label": "Permits so far this year", "value": f"{ytd['total']:,}",
                      "hint": f"{ytd['year']}, through {ytd.get('last_permit_issued', ytd['as_of'])}; "
                              f"{ytd['new_homes']['count']:,} new homes. A partial year, not comparable to full years."})

    span_all = f"{first_all}–{latest}"
    charts = [
        {"type": "trend", "title": "Permits issued per year since 1999",
         "points": [{"x": str(r["year"]), "y": r["total"]} for r in all_complete]},
        {"type": "trend", "title": "Permits by type, per year since 2015",
         "lines": [{"label": GROUP_LABELS[g], "points": [{"x": str(r["year"]), "y": r[g]["count"]} for r in complete]}
                   for g in ("home_improvements", "commercial", "new_homes", "demolitions")]},
        {"type": "bars", "title": "Permits by type, last full year",
         "series": [{"label": GROUP_LABELS[g], "value": last[g]["count"]} for g in GROUPS if last[g]["count"] > 0]},
        {"type": "trend", "title": "New-home permits per year since 2015",
         "points": [{"x": str(r["year"]), "y": r["new_homes"]["count"]} for r in complete]},
    ]

    return {
        "title": "Building Permits",
        "subtitle": f"Homes built, repaired and demolished, {span_all}, from City permit records",
        "lastUpdated": data["extracted"][:7],
        "stats": stats,
        "charts": charts,
        "source": ("City of Burton Building Department permit records, as recorded by the City Assessor (BS&A). "
                   f"Aggregates extracted {data['extracted']}."),
        "links": [
            {"text": "Search City building-department records (BS&A Online)", "href": "https://bsaonline.com/?uid=209"},
            {"text": "Housing in Burton", "href": "#housing"},
            {"text": "Zoning", "href": "#zoning"},
        ],
        "notes": [
            "These are permits issued by the City's Building Department and recorded by the City Assessor. A permit "
            "is permission to do work, not proof the work was finished; the completion time counts only permits "
            "with a recorded final inspection.",
            "Site permits are counted too: roofing, siding, fences, sheds, decks and pools make up most of the "
            "home-improvement total, so a busy year is not always a year of large projects.",
            "Declared value is what the applicant states on the application and is often left blank. It is shown "
            "only where nearly every permit carries one, and it is an estimate, not a measured cost.",
            f"The current year is partial and is left out of the yearly charts. Only counts and totals are "
            f"published, never addresses, owners, contractors or permit numbers. Years before 1999 are not shown "
            f"because the records are incomplete.",
        ],
    }


def main() -> int:
    data = validate_permits(load_json(DATA_FILE), DATA_FILE)
    panel = build_panel(data)
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    for s in panel["stats"]:
        print(f"  {s['label']}: {s['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
