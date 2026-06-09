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
BOUNDARY = os.path.join(ROOT, "public", "boundary.geojson")
GENESEE = "049"
COND_COLS = ("DECK_COND_058", "SUPERSTRUCTURE_COND_059",
             "SUBSTRUCTURE_COND_060", "CULVERT_COND_062")
COND_COLOR = {"Good": "#4ea735", "Fair": "#e08a00", "Poor": "#c0392b"}


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

    cond = Counter(_condition(r) or "Unrated" for r in burton)
    years = [int(r["YEAR_BUILT_027"]) for r in burton if (r.get("YEAR_BUILT_027") or "").strip().isdigit()]
    adt = sum(int(r["ADT_029"]) for r in burton if (r.get("ADT_029") or "").strip().isdigit())
    total = len(burton)
    good = cond.get("Good", 0)

    decade = Counter()
    for y in years:
        decade[(y // 10) * 10] += 1

    stats = [
        {"label": "Bridges in Burton", "value": str(total), "hint": f"FHWA NBI {args.year}"},
        {"label": "In good condition", "value": f"{good}", "hint": f"{round(100*good/total)}% of bridges"},
        {"label": "Needing repair (poor)", "value": f"{cond.get('Poor', 0)}",
         "hint": "significant repair needed"},
        {"label": "Daily crossings", "value": f"{adt:,}", "hint": "vehicles/day (total)"},
        {"label": "Oldest bridge", "value": str(min(years)) if years else "n/a"},
    ]
    charts = [
        {"type": "donut", "title": "Bridge condition (FHWA rating)",
         "series": [{"label": k, "value": cond[k], "color": COND_COLOR[k]}
                    for k in ("Good", "Fair", "Poor") if cond.get(k)]},
        {"type": "bars", "title": "Bridges by decade built", "unit": "",
         "series": [{"label": f"{d}s", "value": decade[d]} for d in sorted(decade)]},
    ]
    panel = {
        "title": "Bridges & Infrastructure",
        "subtitle": f"Burton's road bridges -- FHWA National Bridge Inventory ({args.year})",
        "stats": stats,
        "charts": charts,
        "source": f"Federal Highway Administration (FHWA) National Bridge Inventory, "
                  f"{args.year}, bridges within the City of Burton.",
        "links": [{"text": "FHWA InfoBridge", "href": "https://infobridge.fhwa.dot.gov/"}],
        "notes": [
            "Condition is the federal Good/Fair/Poor rating (the lowest of a "
            "bridge's deck, superstructure, substructure, and culvert ratings). "
            "\"Fair\" is serviceable; \"Poor\" means significant repair is needed -- "
            "not that a bridge is unsafe or closed.",
            "Includes bridges of all owners (city, county, and state) located within "
            "Burton. Source: FHWA NBI; not endorsed or certified by FHWA.",
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT}")
    print(f"  bridges={total} condition={dict(cond)} oldest={min(years) if years else None} adt={adt:,}")
    print(f"  by decade: {dict(sorted(decade.items()))}")


if __name__ == "__main__":
    main()
