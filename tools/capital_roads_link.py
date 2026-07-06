"""Tie funded capital road projects to the Roads & Pavement (PASER) dashboard.

Reads the curated capital-projects.csv, finds the Major/Local Streets project road
names, and marks the matching rows of the Roads dashboard's "Federal-aid roads"
table with a "Funded FY2026-27" indicator (plus a cross-link to Capital Projects).

Pure matching logic (normalize_road / funded_keys / annotate_table) is unit-tested;
annotate_roads_file does the file IO. Idempotent. Stdlib only.

Run standalone:  python tools/capital_roads_link.py
Also invoked automatically at the end of build_capitalprojects.py so the link stays
in sync whenever the capital data changes.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re

from lib.iox import write_geojson, write_json
from lib.paths import pipeline_data_path, public_path

CSV_IN = pipeline_data_path("capital-projects.csv")
ROADS_JSON = public_path("info-roads.json")
PASER_GEOJSON = public_path("paser-roads.geojson")
BOUNDARY_GEOJSON = public_path("boundary.geojson")
OVERLAY_GEOJSON = public_path("capital-roads.geojson")
_FUNDED_COLOR = "#7b1fa2"   # bold purple, distinct from PASER condition colors

STREET_CATEGORIES = {"Major Streets", "Local Streets"}
_TYPES = {"rd", "road", "st", "ave", "blvd", "hwy", "dr", "ln", "ct", "way",
          "pkwy", "trl", "trail"}
_DIRS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}
_STOP = {"project", "reconstruction", "sidewalk", "paving", "improvements",
         "resurfacing", "upgrade", "repair", "non"}
_IMPROVEMENT_COL = "Improvement"
_IMPROVEMENT_VAL = "Funded FY2026-27"
_LINK = {"text": "Capital Projects (what's funded to fix it)", "href": "#capital"}
_NOTE = ("Roads marked \"Funded FY2026-27\" have a funded project in the City's adopted "
         "capital plan; see the Capital Projects dashboard for the full list and cost.")


def normalize_road(name: str) -> str:
    """Reduce a road or project name to a comparable core key.

    Drops a "(from-to)" segment, a leading direction, and everything from the first
    street-type token onward (so "N Genesee Rd" and "Genesee Rd reconstruction" both
    become "genesee"). A name with no type token keeps its words up to a descriptor.
    """
    s = re.sub(r"\(.*?\)", " ", name.lower())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    toks = s.split()
    if toks and toks[0] in _DIRS:
        toks = toks[1:]
    out = []
    for t in toks:
        if t in _TYPES or t in _STOP:
            break
        out.append(t)
    return " ".join(out).strip()


def funded_keys(rows: list) -> set:
    """Normalized road keys for Major/Local Streets projects in the capital rows."""
    keys = set()
    for r in rows:
        if (r.get("category") or "").strip() in STREET_CATEGORIES:
            k = normalize_road(r.get("project", ""))
            if k:
                keys.add(k)
    return keys


def annotate_table(table: dict, funded: set) -> tuple:
    """Add/refresh an `Improvement` column flagging funded roads. Idempotent.
    Returns (new_table, n_flagged)."""
    cols = [c for c in table.get("columns", []) if c != _IMPROVEMENT_COL]
    drop_at = table.get("columns", []).index(_IMPROVEMENT_COL) if _IMPROVEMENT_COL in table.get("columns", []) else None
    new_rows = []
    n = 0
    for row in table.get("rows", []):
        cells = list(row.get("cells", []))
        if drop_at is not None and drop_at < len(cells):
            cells.pop(drop_at)
        flagged = normalize_road(cells[0]) in funded if cells else False
        cells.append(_IMPROVEMENT_VAL if flagged else "")
        if flagged:
            n += 1
        new_rows.append({**row, "cells": cells})
    return {**table, "columns": cols + [_IMPROVEMENT_COL], "rows": new_rows}, n


def annotate_roads_file(roads_path: str = ROADS_JSON, csv_path: str = CSV_IN) -> int:
    """Annotate the Roads dashboard JSON in place. Returns the number of roads flagged
    (0 if the roads JSON or capital CSV is missing -- a no-op, never an error)."""
    if not (os.path.exists(roads_path) and os.path.exists(csv_path)):
        return 0
    with open(csv_path, encoding="utf-8") as fh:
        funded = funded_keys(list(csv.DictReader(fh)))
    with open(roads_path, encoding="utf-8") as fh:
        panel = json.load(fh)
    tables = panel.get("tables") or []
    if not tables:
        return 0
    panel["tables"][0], n = annotate_table(tables[0], funded)

    links = panel.setdefault("links", [])
    if not any(l.get("href") == _LINK["href"] for l in links):
        links.insert(0, dict(_LINK))
    notes = panel.setdefault("notes", [])
    if _NOTE not in notes:
        notes.insert(0, _NOTE)

    write_json(roads_path, panel)
    return n


def _money(n: int) -> str:
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.0f}k"
    return f"${n:,}"


# ---- geometry: clip a funded project to just its named road section -----------
# Project names carry the section, e.g. "Genesee Rd (Atherton to Court)". We resolve
# each endpoint (a cross-street in the PASER network, or the city boundary for "city
# limits") to a point, then keep only the road's segments that fall between them.
# Planar approximation in degrees (scaled by cos(lat)) is plenty at city scale.
_LAT0 = 43.0
_COS = math.cos(math.radians(_LAT0))


def _xy(pt):
    return (pt[0] * _COS, pt[1])


def _d2(a, b):
    ax, ay = _xy(a)
    bx, by = _xy(b)
    return (ax - bx) ** 2 + (ay - by) ** 2


def _road_index(paser_fc: dict) -> dict:
    """key -> {segs: [feature], verts: [(lon,lat)]} for every PASER road."""
    idx = {}
    for f in paser_fc.get("features", []):
        key = normalize_road((f.get("properties") or {}).get("name", ""))
        if not key:
            continue
        coords = (f.get("geometry") or {}).get("coordinates") or []
        e = idx.setdefault(key, {"segs": [], "verts": []})
        e["segs"].append(f)
        e["verts"].extend(tuple(c) for c in coords)
    return idx


def _boundary_verts(boundary_fc: dict) -> list:
    geom = boundary_fc.get("geometry") if boundary_fc.get("type") == "Feature" else boundary_fc
    if not geom and boundary_fc.get("features"):
        geom = boundary_fc["features"][0].get("geometry")
    verts = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            verts.append(tuple(c))
        else:
            for x in (c or []):
                walk(x)
    walk((geom or {}).get("coordinates"))
    return verts


def _nearest(target_verts: list, ref_verts: list):
    best, bd = None, None
    for tv in target_verts:
        for rv in ref_verts:
            d = _d2(tv, rv)
            if bd is None or d < bd:
                bd, best = d, tv
    return best


def parse_section(project: str):
    """Return (from, to) cross-street labels from a "(... to ...)" project name, else None."""
    m = re.search(r"\((.*?)\)", project)
    if not m:
        return None
    inside = m.group(1)
    for sep in (" to ", " thru ", " - ", "-"):
        if sep in inside:
            a, b = inside.split(sep, 1)
            return a.strip(), b.strip()
    return None


def _endpoint(label: str, target_verts: list, idx: dict, boundary_verts: list):
    """Resolve a section endpoint to a point on the target road (or None)."""
    if "limit" in label.lower():
        return _nearest(target_verts, boundary_verts) if boundary_verts else None
    key = normalize_road(label)
    if key in idx:
        return _nearest(target_verts, idx[key]["verts"])
    return None


def _clip(segs: list, from_pt, to_pt) -> list:
    """Keep segments whose midpoint projects within [from, to] along the straight axis."""
    fx, fy = _xy(from_pt)
    tx, ty = _xy(to_pt)
    vx, vy = tx - fx, ty - fy
    vv = vx * vx + vy * vy
    if vv == 0:
        return segs
    out = []
    for s in segs:
        cs = (s.get("geometry") or {}).get("coordinates") or []
        if not cs:
            continue
        mid = ((cs[0][0] + cs[-1][0]) / 2, (cs[0][1] + cs[-1][1]) / 2)  # segment midpoint
        mx, my = _xy(mid)
        t = ((mx - fx) * vx + (my - fy) * vy) / vv
        if -0.06 <= t <= 1.06:
            out.append(s)
    return out


def _overlay_feature(name, project, amount, geometry):
    return {
        "type": "Feature",
        "properties": {
            "name": name, "_color": _FUNDED_COLOR, "_weight": 6,
            "_popupRows": [
                ["Status", "Funded for improvement"],
                ["Capital plan", "FY2026-27"],
                ["Project", project],
                ["Budgeted", _money(amount)],
            ],
        },
        "geometry": geometry,
    }


def build_overlay(paser_fc: dict, street_rows: list, boundary_fc=None) -> dict:
    """Build the funded-road overlay, each project clipped to its named section. A
    project whose section (or road) can't be resolved is left OFF the map rather than
    drawn as the whole road. Pure."""
    idx = _road_index(paser_fc)
    bverts = _boundary_verts(boundary_fc or {})
    feats = []
    for row in street_rows:
        project = (row.get("project") or "").strip()
        road = idx.get(normalize_road(project))
        if not road:
            continue                                # not a federal-aid road we map
        try:
            amt = int(round(float(str(row.get("amount", "0")).replace(",", "") or 0)))
        except (TypeError, ValueError):
            amt = 0
        sec = parse_section(project)
        if not sec:
            continue                                # no named section -> don't whole-road it
        pf = _endpoint(sec[0], road["verts"], idx, bverts)
        pt = _endpoint(sec[1], road["verts"], idx, bverts)
        if not (pf and pt):
            continue                                # endpoints unresolvable -> skip
        for s in _clip(road["segs"], pf, pt):
            feats.append(_overlay_feature((s.get("properties") or {}).get("name", ""),
                                          project, amt, s.get("geometry")))
    return {
        "type": "FeatureCollection",
        "_source": "City of Burton adopted FY2026-27 capital plan, each project clipped to its "
                   "named road section on the Genesee County (GCMPC) PASER federal-aid network.",
        "features": feats,
    }


def build_overlay_file(paser_path: str = PASER_GEOJSON, csv_path: str = CSV_IN,
                       boundary_path: str = BOUNDARY_GEOJSON, out_path: str = OVERLAY_GEOJSON) -> int:
    """Write capital-roads.geojson. Returns the number of segments (0 = no-op)."""
    if not (os.path.exists(paser_path) and os.path.exists(csv_path)):
        return 0
    with open(csv_path, encoding="utf-8") as fh:
        street_rows = [r for r in csv.DictReader(fh)
                       if (r.get("category") or "").strip() in STREET_CATEGORIES]
    with open(paser_path, encoding="utf-8") as fh:
        paser = json.load(fh)
    boundary = {}
    if os.path.exists(boundary_path):
        with open(boundary_path, encoding="utf-8") as fh:
            boundary = json.load(fh)
    overlay = build_overlay(paser, street_rows, boundary)
    write_geojson(out_path, overlay)
    return len(overlay["features"])


def link_all() -> tuple:
    """Annotate the roads table + (re)build the funded-roads overlay. Returns
    (rows_flagged, overlay_segments)."""
    return annotate_roads_file(), build_overlay_file()


def main() -> int:
    flagged, segs = link_all()
    print(f"Flagged {flagged} road row(s); wrote {segs} funded-road segment(s) to {OVERLAY_GEOJSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
