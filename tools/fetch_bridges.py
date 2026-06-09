# Build public/info-bridges.json for the Bridges & Infrastructure dashboard.
#
# Source: FHWA National Bridge Inventory (NBI), the public Michigan delimited
# file. Filtered to Genesee County (049) then to bridges inside the Burton city
# boundary (public/boundary.geojson) by latitude/longitude. Public domain.
#
# FHWA "Good / Fair / Poor" condition follows the federal rule: the LOWEST of the
# deck / superstructure / substructure / culvert NBI condition ratings (0-9),
# Good >= 7, Fair 5-6, Poor <= 4. Fair is serviceable, not deficient; Poor means
# significant repair is needed (not that a bridge is unsafe / closed).
#
# Re-runnable (committed output; the site reads the JSON, never FHWA):
#   python tools/fetch_bridges.py [--year 2024]
#
# Stdlib only (urllib/csv/json).
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "public", "info-bridges.json")
OUT_GEOJSON = os.path.join(ROOT, "public", "bridges.geojson")
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
GENESEE = "049"
COND_COLS = ("DECK_COND_058", "SUPERSTRUCTURE_COND_059",
             "SUBSTRUCTURE_COND_060", "CULVERT_COND_062")
COND_COLOR = {"Good": "#4ea735", "Fair": "#e08a00", "Poor": "#c0392b"}
COND_FALLBACK = "#888888"  # Unrated / unknown condition marker color
# NBI item 22 owner code -> who maintains the bridge.
OWNER_LABELS = {
    "01": "State", "02": "County", "03": "Township", "04": "City",
    "11": "State park", "21": "Other state", "25": "Other local",
    "26": "Private", "27": "Railroad", "31": "State toll", "32": "Local toll",
}


def _int(s) -> int:
    s = (s or "").strip()
    return int(s) if s.isdigit() else 0


def _dms(s: str | None, deg_digits: int) -> float | None:
    """NBI packed DMS ('43015937' / '083554218') -> signed decimal degrees."""
    s = (s or "").strip()
    if not s.isdigit() or set(s) == {"0"}:
        return None
    s = s.zfill(deg_digits + 6)
    d = int(s[:deg_digits]); m = int(s[deg_digits:deg_digits + 2])
    sec = int(s[deg_digits + 2:deg_digits + 4]) + int(s[deg_digits + 4:deg_digits + 6]) / 100
    return d + m / 60 + sec / 3600


def _load_rings() -> list:
    b = json.load(open(BOUNDARY, encoding="utf-8"))
    geom = b["features"][0]["geometry"] if b.get("type") == "FeatureCollection" else b.get("geometry", b)
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [ring for poly in polys for ring in poly]


def _inside(lon: float, lat: float, rings: list) -> bool:
    inside = False
    for ring in rings:
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
            if ((y1 > lat) != (y2 > lat)) and (lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1):
                inside = not inside
    return inside


def _condition(r: dict) -> str | None:
    vals = [int(r[c]) for c in COND_COLS if (r.get(c) or "").strip().isdigit()]
    if not vals:
        return None
    lo = min(vals)
    return "Good" if lo >= 7 else "Fair" if lo >= 5 else "Poor"


def _cond_pct(rows: list) -> dict:
    """Good/Fair/Poor percentages (rounded ints) over the rows that have a
    determinable FHWA condition. Unrated rows are excluded from the denominator,
    matching how FHWA reports the Good/Fair/Poor split."""
    c = Counter(cond for cond in (_condition(r) for r in rows) if cond)
    n = sum(c.values())
    return {k: round(100 * c.get(k, 0) / n) for k in ("Good", "Fair", "Poor")} if n else {}


def build_compare(burton: list, genesee: list, michigan: list) -> dict:
    """A 'compare' chart: Burton (subject) vs Genesee County vs Michigan statewide,
    one grouped metric per condition. All three computed from the same NBI file."""
    bp, gp, mp = _cond_pct(burton), _cond_pct(genesee), _cond_pct(michigan)
    return {
        "type": "compare",
        "title": "How Burton compares -- bridge condition",
        "rows": [
            {"label": f"{k} condition", "unit": "%", "values": [
                {"name": "Burton", "value": bp.get(k, 0)},
                {"name": "Genesee Co.", "value": gp.get(k, 0)},
                {"name": "Michigan", "value": mp.get(k, 0)},
            ]}
            for k in ("Good", "Fair", "Poor")
        ],
    }


def _carries_crosses(r: dict) -> tuple[str, str]:
    carries = (r.get("FACILITY_CARRIED_007") or "").strip().strip("'\"")
    crosses = (r.get("FEATURES_DESC_006A") or "").strip().strip("'\"")
    return carries, crosses


def build_bridges_table(burton: list) -> dict:
    """A per-bridge table (busiest first): name, condition (+color dot), year,
    daily traffic, owner -- the 'what are the bridges' detail for the dashboard."""
    rows = []
    for r in sorted(burton, key=lambda r: _int(r.get("ADT_029")), reverse=True):
        cond = _condition(r) or "Unrated"
        carries, crosses = _carries_crosses(r)
        name = f"{carries} over {crosses}" if carries and crosses else (carries or crosses or "Bridge")
        year = (r.get("YEAR_BUILT_027") or "").strip()
        adt = _int(r.get("ADT_029"))
        owner = OWNER_LABELS.get((r.get("OWNER_022") or "").strip(), "Other")
        rows.append({
            "cells": [name, cond, year if year.isdigit() else "n/a",
                      f"{adt:,}" if adt else "n/a", owner],
            "color": COND_COLOR.get(cond, COND_FALLBACK),
        })
    return {
        "title": "Every bridge in Burton",
        "columns": ["Bridge", "Condition", "Built", "Daily traffic", "Maintained by"],
        "rows": rows,
    }


def _bridge_point(r: dict) -> dict | None:
    """One NBI row -> a condition-colored GeoJSON Point feature, or None if it has
    no usable coordinates. NBI packs longitude as a positive West value, so the
    geographic longitude (and the x in [lon, lat]) is NEGATIVE: -lon."""
    lat = _dms(r.get("LAT_016"), 2)
    lon = _dms(r.get("LONG_017"), 3)
    if not (lat and lon):
        return None
    cond = _condition(r) or "Unrated"
    carries, crosses = _carries_crosses(r)
    adt = _int(r.get("ADT_029"))
    year = (r.get("YEAR_BUILT_027") or "").strip()
    owner = OWNER_LABELS.get((r.get("OWNER_022") or "").strip(), "Other")
    name = f"{carries} over {crosses}" if carries and crosses else (carries or crosses or "Bridge")
    # [label, value] pairs the viewer renders as an escaped popup table, under the
    # name heading (which already states what the bridge carries / crosses).
    rows = [["Condition", cond]]
    if adt:
        rows.append(["Traffic", f"{adt:,}/day"])
    if year.isdigit():
        rows.append(["Built", year])
    rows.append(["Maintained by", owner])
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(-lon, 5), round(lat, 5)]},
        "properties": {
            "name": name,
            "condition": cond,
            "_color": COND_COLOR.get(cond, COND_FALLBACK),
            "_popupRows": rows,
        },
    }


def build_bridges_geojson(rows: list) -> dict:
    """Pure NBI-rows -> GeoJSON FeatureCollection of condition-colored bridge points."""
    feats = [f for f in (_bridge_point(r) for r in rows) if f]
    return {"type": "FeatureCollection", "features": feats}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", default="2024", help="NBI publication year")
    args = ap.parse_args()
    url = f"https://www.fhwa.dot.gov/bridge/nbi/{args.year}/delimited/MI{args.year[2:]}.txt"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        rows = list(csv.DictReader(io.StringIO(resp.read().decode("latin-1"))))

    rings = _load_rings()
    burton = []
    for r in rows:
        if (r.get("COUNTY_CODE_003") or "").strip() != GENESEE:
            continue
        lat = _dms(r.get("LAT_016"), 2)
        lon = _dms(r.get("LONG_017"), 3)
        if lat and lon and _inside(-lon, lat, rings):   # NBI longitude is West (negative)
            burton.append(r)
    if not burton:
        sys.exit("No Burton bridges found inside the boundary")

    # County + statewide pools for the comparison chart -- same file, same FHWA rule.
    genesee = [r for r in rows if (r.get("COUNTY_CODE_003") or "").strip() == GENESEE]
    michigan = rows

    cond = Counter(_condition(r) or "Unrated" for r in burton)
    years = [int(r["YEAR_BUILT_027"]) for r in burton if (r.get("YEAR_BUILT_027") or "").strip().isdigit()]
    adt = sum(_int(r.get("ADT_029")) for r in burton)
    total = len(burton)
    good = cond.get("Good", 0)

    decade = Counter()
    for y in years:
        decade[(y // 10) * 10] += 1

    # Who maintains them (NBI owner code).
    owner = Counter(OWNER_LABELS.get((r.get("OWNER_022") or "").strip(), "Other") for r in burton)

    # Busiest bridge: highest daily traffic + what it carries / crosses.
    busiest = max(burton, key=lambda r: _int(r.get("ADT_029")))
    carries = (busiest.get("FACILITY_CARRIED_007") or "").strip().strip("'\"") or "a road"
    crosses = (busiest.get("FEATURES_DESC_006A") or "").strip().strip("'\"")
    busiest_adt = _int(busiest.get("ADT_029"))
    busiest_hint = f"{carries} over {crosses}" if crosses else carries

    # Total deck length carried by Burton's bridges (NBI structure length, metres -> feet).
    total_len_ft = round(sum(float(r["STRUCTURE_LEN_MT_049"]) for r in burton
                             if (r.get("STRUCTURE_LEN_MT_049") or "").replace(".", "", 1).strip().isdigit()) * 3.281)

    stats = [
        {"label": "Bridges in Burton", "value": str(total), "hint": f"FHWA NBI {args.year}"},
        {"label": "In good condition", "value": f"{good}", "hint": f"{round(100*good/total)}% of bridges"},
        {"label": "Needing repair (poor)", "value": f"{cond.get('Poor', 0)}",
         "hint": "significant repair needed"},
        {"label": "Busiest bridge", "value": f"{busiest_adt:,}/day", "hint": busiest_hint},
        {"label": "City-maintained", "value": f"{owner.get('City', 0)}",
         "hint": f"vs {owner.get('State', 0)} state, {owner.get('County', 0)} county"},
        {"label": "Oldest bridge", "value": str(min(years)) if years else "n/a"},
    ]
    charts = [
        {"type": "donut", "title": "Bridge condition (FHWA rating)",
         "series": [{"label": k, "value": cond[k], "color": COND_COLOR[k]}
                    for k in ("Good", "Fair", "Poor") if cond.get(k)]},
        {"type": "bars", "title": "Who maintains them", "unit": "",
         "series": [{"label": k, "value": v} for k, v in owner.most_common()]},
        {"type": "bars", "title": "Bridges by decade built", "unit": "",
         "series": [{"label": f"{d}s", "value": decade[d]} for d in sorted(decade)]},
    ]
    # Burton vs Genesee County vs Michigan, right after the Burton condition donut.
    charts.insert(1, build_compare(burton, genesee, michigan))
    panel = {
        "title": "Bridges & Infrastructure",
        "subtitle": f"Burton's road bridges -- FHWA National Bridge Inventory ({args.year})",
        "stats": stats,
        "charts": charts,
        "tables": [build_bridges_table(burton)],
        "source": f"Federal Highway Administration (FHWA) National Bridge Inventory, "
                  f"{args.year}, bridges within the City of Burton.",
        "links": [{"text": "FHWA InfoBridge", "href": "https://infobridge.fhwa.dot.gov/"}],
        "notes": [
            "Condition is the federal Good/Fair/Poor rating (the lowest of a "
            "bridge's deck, superstructure, substructure, and culvert ratings). "
            "\"Fair\" is serviceable; \"Poor\" means significant repair is needed -- "
            "not that a bridge is unsafe or closed.",
            f"Covers all {total} bridges within Burton regardless of owner -- the city "
            f"maintains {owner.get('City', 0)}, the rest are state or county "
            f"(e.g. the I-69 and I-475 overpasses). Together they carry about "
            f"{total_len_ft:,} ft of deck.",
            f"The comparison is by bridge count (not deck area) using the same FHWA file: "
            f"Genesee County ({len(genesee)} bridges) and Michigan statewide are tallied by "
            f"the identical Good/Fair/Poor rule. With only {total} bridges, each Burton bridge "
            f"is about {round(100/total)}% -- the comparison shows the broad pattern, not a precise rank.",
            "Source: FHWA NBI; not endorsed or certified by FHWA.",
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT}")
    print(f"  bridges={total} condition={dict(cond)} oldest={min(years) if years else None} adt={adt:,}")
    print(f"  by decade: {dict(sorted(decade.items()))}")
    # Cross-check the comparison tiers (verify Michigan vs FHWA's published split).
    print(f"  condition %%: Burton={_cond_pct(burton)} "
          f"Genesee(n={len(genesee)})={_cond_pct(genesee)} "
          f"Michigan(n={len(michigan)})={_cond_pct(michigan)}")

    # Per-bridge map overlay: condition-colored points the viewer toggles on.
    geojson = build_bridges_geojson(burton)
    with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"Wrote {OUT_GEOJSON} ({len(geojson['features'])} points)")


if __name__ == "__main__":
    main()
