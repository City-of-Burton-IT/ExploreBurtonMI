# Fold the Fire Chief's annual summary workbooks into the Public Safety
# (Fire & Rescue) dashboard as MULTI-YEAR trend charts.
#
# Source: five hand-maintained summary workbooks the Fire Chief's office keeps
# (City of Burton OneDrive "ExploreBurton App/"). These are pure AGGREGATES
# (counts by year / station / month) -- no addresses, names, or per-incident
# rows -- so unlike the Emergency Networking exports the dashboard's base panel
# is built from, they carry no PII and may be committed as a derived fragment.
#
# This tool reads them and ADDS historical trend charts to the existing panel:
#   * Annual Stats.xlsx          -> Total calls for service by year (2014-2025)
#   * Station Comparison.xlsx     -> Calls by station area (latest full year)
#   * Monthly Average Worksheet   -> Busiest months (multi-year monthly average)
#   * Annual Comparison.xlsx / Quarterly Statistics.xlsx -> reviewed, NOT charted
#     (Quarterly is redundant with the annual + monthly views; the mutual-aid
#     series from Annual Comparison was removed at the department's request).
#
# GOVERNANCE:
#   * The current-year snapshot (stats + "by type" NFIRS chart) stays as the
#     Emergency Networking base panel already has it. These additions are
#     historical TIME-SERIES only; they never restate the NFIRS taxonomy (the
#     workbook's plain-language categories don't reconcile 1:1 with NFIRS
#     series, so juxtaposing them would invite "these don't add up").
#   * Year totals come from Annual Stats / Station Comparison (2025 = 758,
#     matching the live headline). The Monthly worksheet (NFIRS-station based,
#     2025 sums to 748) is used ONLY for month-to-month SHAPE (seasonality),
#     never for an annual total -- the two sources are never crossed in a chart.
#   * The merge is idempotent (charts/notes this tool owns are replaced, not
#     duplicated) and the same PII guard from build_publicsafety runs on the
#     final panel before it is written.
#
# Re-runnable:
#   python tools/build_fire_trends.py
#   python tools/build_fire_trends.py --src "PATH\to\ExploreBurton App"
#
# Requires: openpyxl (see tools/requirements.txt).
from __future__ import annotations

import argparse
import json
import os
import sys

import openpyxl

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PANEL = os.path.join(REPO_ROOT, "public", "info-publicsafety.json")
CACHE = os.path.join(os.path.dirname(__file__), "fire-trends.json")
# The Fire Chief's workbooks live in the user's OneDrive by default.
DEFAULT_SRC = os.path.join(
    os.path.expanduser("~"),
    "OneDrive - City of Burton", "ExploreBurton App",
)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Chart titles and the note marker this tool OWNS. Anything matching is removed
# before re-adding, so repeated runs (or a build_publicsafety merge) never
# duplicate. Titles carry the year range, so they are built, not literals.
HISTORY_MARK = "Multi-year trends are from the Fire Department's annual summary"

# Chart-title prefixes this tool no longer emits but that may linger in an
# already-merged panel. merge_into_panel strips them so a re-run cleans them up
# (e.g. the mutual-aid chart, removed at the department's request).
DEPRECATED_TITLE_PREFIXES = ("Mutual aid given to neighbors",)


# --- workbook readers ------------------------------------------------------

def _rows(path: str) -> list[tuple]:
    """Return all cell rows of the first worksheet (values only)."""
    if not os.path.isfile(path):
        sys.exit(f"ERROR: workbook not found: {path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    return rows


def _year_header(row: tuple) -> dict[int, int]:
    """Map {year -> column index} from a header row of 4-digit years."""
    out: dict[int, int] = {}
    for i, cell in enumerate(row):
        if isinstance(cell, (int, float)) and 1900 <= int(cell) <= 2100:
            out[int(cell)] = i
    return out


def _label(cell) -> str:
    return str(cell or "").strip()


def parse_total_by_year(path: str) -> list[dict]:
    """Annual Stats.xlsx -> [{year, total}] for the 'Total Calls for Service'
    row, one point per full calendar year in the header."""
    rows = _rows(path)
    years = _year_header(rows[0])
    if not years:
        sys.exit(f"ERROR: no year header in {os.path.basename(path)}")
    total_row = next(
        (r for r in rows[1:]
         if _label(r[0]).lower().startswith("total calls for service")),
        None,
    )
    if total_row is None:
        sys.exit(f"ERROR: no 'Total Calls for Service' row in {os.path.basename(path)}")
    points = []
    for yr in sorted(years):
        ci = years[yr]
        v = total_row[ci] if ci < len(total_row) else None
        if isinstance(v, (int, float)):
            points.append({"year": yr, "total": int(v)})
    return points


def parse_station_latest(path: str) -> dict:
    """Station Comparison.xlsx -> {'year': Y, 'stations': [(name, calls)...]}
    for the latest data year (the last numeric YEAR row)."""
    rows = _rows(path)
    header = rows[0]
    # locate the YEAR column and the station columns by header text
    hi = {_label(c).upper(): i for i, c in enumerate(header)}
    year_i = next((i for k, i in hi.items() if k == "YEAR"), None)
    station_cols = [(_label(header[i]), i) for i in range(len(header))
                    if _label(header[i]).upper().startswith("STA")]
    if year_i is None or not station_cols:
        sys.exit(f"ERROR: missing YEAR/STA columns in {os.path.basename(path)}")
    latest_year = None
    latest = None
    for r in rows[1:]:
        yv = r[year_i] if year_i < len(r) else None
        if not isinstance(yv, (int, float)):
            continue  # skips Total:/Annual Avg: footer rows
        if latest_year is None or int(yv) > latest_year:
            latest_year = int(yv)
            latest = r
    if latest is None:
        sys.exit(f"ERROR: no numeric year rows in {os.path.basename(path)}")
    stations = []
    for name, ci in station_cols:
        v = latest[ci] if ci < len(latest) else None
        if isinstance(v, (int, float)):
            # "STA. #1" -> "Station 1 area"
            label = name.replace("STA.", "Station").replace("#", "").strip()
            stations.append((f"{label} area", int(v)))
    return {"year": latest_year, "stations": stations}


def parse_monthly_average(path: str) -> dict:
    """Monthly Average Worksheet.xlsx -> {'years': [..], 'avg': [12 floats]}.
    Averages only FULL calendar years (all 12 months present), excluding any
    partial current year, so the seasonality shape is clean and self-consistent."""
    rows = _rows(path)
    # header: ['', January, February, ... December, Total] -> month columns 1..12
    month_cols = list(range(1, 13))
    sums = [0.0] * 12
    counts = [0] * 12
    used_years: list[int] = []
    for r in rows[1:]:
        yv = r[0] if r else None
        if not isinstance(yv, (int, float)):
            continue  # skips AVG. / blank / footnote rows
        vals = [r[c] if c < len(r) else None for c in month_cols]
        if not all(isinstance(v, (int, float)) for v in vals):
            continue  # partial year (e.g. current year through March) -> skip
        used_years.append(int(yv))
        for m in range(12):
            sums[m] += float(vals[m])
            counts[m] += 1
    avg = [round(sums[m] / counts[m], 1) if counts[m] else 0.0 for m in range(12)]
    return {"years": sorted(used_years), "avg": avg}


# --- chart assembly --------------------------------------------------------

def build_fragment(src: str) -> dict:
    """Read the workbooks under `src` and return {charts, stats, notes} to merge."""
    totals = parse_total_by_year(os.path.join(src, "Annual Stats.xlsx"))
    station = parse_station_latest(os.path.join(src, "Station Comparison.xlsx"))
    monthly = parse_monthly_average(os.path.join(src, "Monthly Average Worksheet.xlsx"))

    charts: list[dict] = []

    if totals:
        y0, y1 = totals[0]["year"], totals[-1]["year"]
        charts.append({
            "type": "trend",
            "title": f"Total calls for service by year ({y0}-{y1})",
            "unit": "",
            "points": [{"x": str(p["year"]), "y": p["total"]} for p in totals],
        })

    if station["stations"]:
        charts.append({
            "type": "bars",
            "title": f"Calls by station area ({station['year']})",
            "unit": "",
            "series": [{"label": n, "value": v} for n, v in station["stations"]],
        })

    if monthly["years"]:
        ys = monthly["years"]
        span = f"{ys[0]}-{ys[-1]}" if len(ys) > 1 else str(ys[0])
        charts.append({
            "type": "bars",
            "title": f"Busiest months ({span} average)",
            "unit": "",
            "series": [{"label": MONTHS[m], "value": monthly["avg"][m]}
                       for m in range(12)],
        })

    # A trend stat: growth over the available annual span.
    stats: list[dict] = []
    if len(totals) >= 2 and totals[0]["total"] > 0:
        first, last = totals[0], totals[-1]
        pct = round((last["total"] - first["total"]) / first["total"] * 100)
        stats.append({
            "label": f"{last['year'] - first['year']}-year change",
            "value": f"{pct:+d}%",
            "hint": f"{first['total']:,} ({first['year']}) -> "
                    f"{last['total']:,} ({last['year']})",
        })

    note = (
        "Multi-year trends are from the Fire Department's annual summary "
        "workbooks (calls for service by year, station, and month), maintained "
        "by the Fire Chief's office. Year totals are full calendar years. "
        "Month averages show seasonality from a separate monthly tally, so "
        "their yearly sum differs slightly from the annual totals."
    )
    return {"charts": charts, "stats": stats, "notes": [note]}


def merge_into_panel(panel: dict, fragment: dict) -> dict:
    """Idempotently fold the fragment's charts/stats/notes into a panel. Charts
    and notes this tool owns are removed first, so repeated runs do not stack."""
    owned_titles = {c["title"] for c in fragment["charts"]}

    def _keep(chart: dict) -> bool:
        t = chart.get("title", "")
        if t in owned_titles:
            return False  # this tool re-adds it below
        return not t.startswith(DEPRECATED_TITLE_PREFIXES)

    panel["charts"] = [c for c in panel.get("charts", []) if _keep(c)] + fragment["charts"]

    owned_stat_labels = {s["label"] for s in fragment["stats"]}
    panel["stats"] = [s for s in panel.get("stats", [])
                      if s.get("label") not in owned_stat_labels] + fragment["stats"]

    notes = [n for n in panel.get("notes", []) if not n.startswith(HISTORY_MARK)]
    # keep the trailing "Draft -- ..." note last if present
    draft = [n for n in notes if n.startswith("Draft")]
    notes = [n for n in notes if not n.startswith("Draft")]
    panel["notes"] = notes + fragment["notes"] + draft
    return panel


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=DEFAULT_SRC,
                    help="folder holding the Fire Chief's summary .xlsx workbooks")
    ap.add_argument("--panel", default=PANEL, help="info-publicsafety.json to update")
    ap.add_argument("--cache", default=CACHE,
                    help="committable fragment cache (read by build_publicsafety)")
    args = ap.parse_args()

    fragment = build_fragment(args.src)

    with open(args.cache, "w", encoding="utf-8") as f:
        json.dump(fragment, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if not os.path.isfile(args.panel):
        sys.exit(f"ERROR: base panel not found: {args.panel}. "
                 "Run build_publicsafety.py first.")
    with open(args.panel, encoding="utf-8") as f:
        panel = json.load(f)

    panel = merge_into_panel(panel, fragment)

    # Reuse the same PII guard the base tool enforces.
    from build_publicsafety import assert_no_pii
    assert_no_pii(panel)

    with open(args.panel, "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {args.cache}")
    print(f"Updated {args.panel}")
    print(f"  added {len(fragment['charts'])} charts, "
          f"{len(fragment['stats'])} stat(s)")
    for c in fragment["charts"]:
        n = len(c.get("points") or c.get("series") or [])
        print(f"    - {c['title']}  ({n} pts)")


if __name__ == "__main__":
    main()
