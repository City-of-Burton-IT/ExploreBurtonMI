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
import re
import sys

from lib.iox import write_json
from lib.paths import public_path

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "data", "bsa-permits.json")
WORKFLOW_FILE = os.path.join(HERE, "data", "bsa-permit-workflow.json")
OUT = public_path("info-permits.json")

INSPECTION_RESULT_KEYS = ("approved", "disapproved", "partially_approved", "not_ready",
                          "locked_out", "canceled", "none")
PERMIT_STATUS_GROUP_KEYS = ("finaled", "closed", "expired", "open", "canceled", "other")
INSPECTION_TYPE_RE = re.compile(r"^[A-Z0-9 &/-]+$")

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


def validate_workflow(data: object, where: str = "permit workflow file") -> dict:
    """Boundary check for the inspections/completion workflow file. A changed status or
    result decode must stop the build, not silently mislabel counts."""
    if not isinstance(data, dict):
        sys.exit(f"{where}: expected an object")
    for key in ("_source", "extracted", "latest_complete_year", "status_codes", "result_codes",
                "inspections_by_year", "inspection_types_latest", "permits_by_issue_year",
                "finished_within_year", "inspections_per_permit"):
        if key not in data:
            sys.exit(f"{where}: missing '{key}'")
    if not isinstance(data["extracted"], str) or len(data["extracted"]) != 10:
        sys.exit(f"{where}: extracted must be an ISO date")
    latest = data["latest_complete_year"]
    if not isinstance(latest, int):
        sys.exit(f"{where}: latest_complete_year must be an integer")

    status_codes = data["status_codes"]
    result_codes = data["result_codes"]
    if (not isinstance(status_codes, dict) or not isinstance(result_codes, dict)
            or status_codes.get("6") != "Finaled" or status_codes.get("7") != "Expired"
            or status_codes.get("14") != "Closed" or result_codes.get("1") != "Approved"
            or result_codes.get("2") != "Disapproved" or result_codes.get("3") != "Partially Approved"):
        sys.exit(f"{where}: status/result code decode has changed; refusing to build on an unverified decode")

    rows = data["inspections_by_year"]
    if not isinstance(rows, list) or not rows:
        sys.exit(f"{where}: inspections_by_year must be a non-empty list")
    seen = set()
    years_in_order = []
    complete_count = 0
    for r in rows:
        year = r.get("year") if isinstance(r, dict) else None
        if not isinstance(year, int) or year in seen:
            sys.exit(f"{where}: inspections_by_year needs unique integer years")
        seen.add(year)
        years_in_order.append(year)
        if not _is_count(r.get("completed")) or not all(_is_count(r.get(k)) for k in INSPECTION_RESULT_KEYS):
            sys.exit(f"{where}: {year} inspections_by_year row needs non-negative integer counts")
        if sum(r[k] for k in INSPECTION_RESULT_KEYS) != r["completed"]:
            sys.exit(f"{where}: {year} inspection result counts do not sum to completed")
        if year <= latest:
            complete_count += 1
            if not 500 <= r["completed"] <= 20000:
                sys.exit(f"{where}: {year} completed {r['completed']} is outside 500 to 20000")
            judged = r["approved"] + r["disapproved"] + r["partially_approved"]
            if judged <= 0 or not 0.5 <= r["approved"] / judged <= 0.98:
                sys.exit(f"{where}: {year} approved share of judged inspections is out of range")
    if years_in_order != sorted(years_in_order):
        sys.exit(f"{where}: inspections_by_year years must be ascending")
    if complete_count < 5:
        sys.exit(f"{where}: inspections_by_year needs at least 5 complete years")
    if latest not in seen:
        sys.exit(f"{where}: no inspections_by_year row for the latest complete year {latest}")

    itl = data["inspection_types_latest"]
    if not isinstance(itl, dict) or not isinstance(itl.get("types"), list) or not itl["types"]:
        sys.exit(f"{where}: inspection_types_latest.types must be a non-empty list")
    for t in itl["types"]:
        if (not isinstance(t, dict) or not isinstance(t.get("type"), str)
                or not INSPECTION_TYPE_RE.match(t["type"])):
            sys.exit(f"{where}: inspection type name is invalid")
        if not all(_is_count(t.get(k)) for k in ("completed", "approved", "disapproved", "partially_approved")):
            sys.exit(f"{where}: inspection type '{t['type']}' needs integer counts")

    piy = data["permits_by_issue_year"]
    if not isinstance(piy, list) or not piy:
        sys.exit(f"{where}: permits_by_issue_year must be a non-empty list")
    for r in piy:
        year = r.get("year") if isinstance(r, dict) else None
        if not isinstance(year, int) or not _is_count(r.get("permits")):
            sys.exit(f"{where}: permits_by_issue_year rows need an integer year and permits")
        total = 0
        for g in ("building", "site", "other"):
            cell = r.get(g)
            if (not isinstance(cell, dict) or not _is_count(cell.get("permits"))
                    or not all(_is_count(cell.get(k)) for k in PERMIT_STATUS_GROUP_KEYS)):
                sys.exit(f"{where}: {year} {g} needs integer permits and status counts")
            if sum(cell[k] for k in PERMIT_STATUS_GROUP_KEYS) != cell["permits"]:
                sys.exit(f"{where}: {year} {g} status counts do not sum to its permits")
            total += cell["permits"]
        if total != r["permits"]:
            sys.exit(f"{where}: {year} group permits do not sum to the row total")
        if year <= latest and not 300 <= r["permits"] <= 3000:
            sys.exit(f"{where}: {year} permits {r['permits']} is outside 300 to 3000")

    fwy = data["finished_within_year"]
    if not isinstance(fwy, dict) or not isinstance(fwy.get("years"), list) or len(fwy["years"]) < 4:
        sys.exit(f"{where}: finished_within_year.years must have at least 4 rows")
    through_year = fwy.get("through_year")
    if not isinstance(through_year, int):
        sys.exit(f"{where}: finished_within_year.through_year must be an integer")
    for r in fwy["years"]:
        if not isinstance(r, dict) or not isinstance(r.get("year"), int) or r["year"] > through_year:
            sys.exit(f"{where}: finished_within_year row year must be an integer no higher than through_year")
        if not _is_count(r.get("permits")) or r["permits"] < 100:
            sys.exit(f"{where}: finished_within_year row permits must be an integer at least 100")
        fw = r.get("finaled_within_year")
        fe = r.get("finaled_ever")
        if not _is_count(fw) or not _is_count(fe) or not (0 <= fw <= fe <= r["permits"]):
            sys.exit(f"{where}: finished_within_year counts must satisfy 0 <= within <= ever <= permits")

    ipp = data["inspections_per_permit"]
    if (not isinstance(ipp, dict) or not _is_count(ipp.get("permits")) or ipp["permits"] < 100
            or not _is_count(ipp.get("inspections"))):
        sys.exit(f"{where}: inspections_per_permit needs an integer permits of at least 100 and integer inspections")

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


def build_workflow(wf: dict) -> tuple[list, list]:
    latest = wf["latest_complete_year"]
    rows = sorted(wf["inspections_by_year"], key=lambda r: r["year"])
    complete = [r for r in rows if r["year"] <= latest]
    last = next(r for r in rows if r["year"] == latest)
    judged = last["approved"] + last["disapproved"] + last["partially_approved"]
    first_year = rows[0]["year"]

    itl = wf["inspection_types_latest"]
    finals = next((t for t in itl["types"] if t["type"] == "FINAL"), None)

    pass_hint = (f"{latest}: approved share of the {judged:,} inspections that were judged "
                 f"(approved, disapproved or partially approved)")
    if finals is not None and judged > 0:
        finals_judged = finals["approved"] + finals["disapproved"] + finals["partially_approved"]
        if finals_judged > 0:
            pass_hint += f"; final inspections {round(100 * finals['approved'] / finals_judged)}%"

    fwy = wf["finished_within_year"]
    fw_years = fwy["years"]
    fw_last = fw_years[-1]
    through_year = fwy["through_year"]
    fw_first = fw_years[0]["year"]

    ipp = wf["inspections_per_permit"]

    stats = [
        {"label": "Inspections completed last year", "value": f"{last['completed']:,}",
         "hint": f"{latest}: inspections on building and site permits; code-enforcement inspections are "
                 f"not counted"},
        {"label": "Inspections passed last year", "value": f"{round(100 * last['approved'] / judged)}%",
         "hint": pass_hint},
        {"label": "Projects finished within a year",
         "value": f"{round(100 * fw_last['finaled_within_year'] / fw_last['permits'])}%",
         "hint": f"building permits issued in {fw_last['year']} that reached a final inspection within "
                 f"12 months; site permits for roofs, fences and sheds are not included"},
        {"label": "Inspections per building permit", "value": f"{ipp['inspections'] / ipp['permits']:.1f}",
         "hint": f"completed inspections per building permit issued in {ipp['year']}"},
    ]

    charts = [
        {"type": "trend", "title": f"Inspection results per year since {first_year}",
         "lines": [
             {"label": "Approved", "points": [{"x": str(r["year"]), "y": r["approved"]} for r in complete]},
             {"label": "Disapproved", "points": [{"x": str(r["year"]), "y": r["disapproved"]} for r in complete]},
             {"label": "Partially approved",
              "points": [{"x": str(r["year"]), "y": r["partially_approved"]} for r in complete]},
         ]},
        {"type": "trend",
         "title": f"Building permits finished within a year of issue, {fw_first} to {through_year}",
         "unit": "%",
         "points": [{"x": str(r["year"]), "y": round(100 * r["finaled_within_year"] / r["permits"], 1)}
                    for r in fw_years]},
        {"type": "bars", "title": f"Inspections completed by type, {latest}",
         "series": [{"label": t["type"].title(), "value": t["completed"]} for t in itl["types"]]},
    ]

    return stats, charts


def build_panel(data: dict, workflow: dict | None = None) -> dict:
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

    notes = [
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
    ]

    if workflow is not None:
        wf_stats, wf_charts = build_workflow(workflow)
        stats = stats + wf_stats
        charts = charts + wf_charts
        notes = notes + [
            "Inspection and completion figures come from the Building Department's own permit system. An "
            "inspection is counted when it is completed; a project counts as finished when its permit reaches "
            "a final inspection within twelve months of issue.",
            "Time from application to issue is not shown because the department records the application date "
            "when the permit is issued, so it measures nothing.",
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
        "notes": notes,
    }


def main() -> int:
    data = validate_permits(load_json(DATA_FILE), DATA_FILE)
    workflow = validate_workflow(load_json(WORKFLOW_FILE), WORKFLOW_FILE)
    panel = build_panel(data, workflow)
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    for s in panel["stats"]:
        print(f"  {s['label']}: {s['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
