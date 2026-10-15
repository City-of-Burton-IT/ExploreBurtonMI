"""Build public/new-homes.geojson: one pin per new-home building permit since the
export's start year, coloured by year band (ADR-0003 Part D).

Shows where Burton is growing. Each feature carries the situs address, the issue
year and the unit count, nothing else: no permit number, owner, contractor, value
or description. A permit is permission to build, not proof the home was finished.

SOURCE: pipeline/data/new-homes.csv from tools/Export-BsaNewHomes.ps1 (gitignored).
Coordinates come from the shared Census batch path and cache; pins outside the
city boundary are dropped.

Re-runnable (committed output; the site reads the file, never the geocoder):
    pipeline/.venv/Scripts/python tools/build_new_homes.py
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from datetime import date

import build_address_points as bap
from lib.iox import write_geojson
from lib.paths import pipeline_data_path, public_path

SOURCE_CSV = pipeline_data_path("new-homes.csv")
CENTROIDS_CSV = pipeline_data_path("parcel-centroids.csv")  # optional, from extract_parcel_centroids.py
OUT = public_path("new-homes.geojson")
REQUIRED = ["street", "year", "units"]
# Year bands, newest darkest. Band edges are relative to the build year so the
# layer does not need re-editing every January.
BAND_COLORS = ["#08519c", "#3182bd", "#6baed6", "#9ecae1"]  # 0-1 yrs, 2-3, 4-6, older


def _norm(s) -> str:
    return " ".join(str(s or "").split()).strip()


def read_rows(path: str = SOURCE_CSV) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"Source not found: {path}\nRun tools/Export-BsaNewHomes.ps1 first.")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise SystemExit(f"new-homes: missing columns {missing}")
        raw = list(reader)
    if not raw:
        raise SystemExit("new-homes: no rows")
    rows = []
    for i, r in enumerate(raw, start=2):
        street = _norm(r["street"])
        parcel = _norm(r.get("parcel"))
        if not street and not parcel:
            continue
        try:
            year = int(float(r["year"]))
            units = int(float(r["units"] or 0))
        except ValueError as exc:
            raise SystemExit(f"new-homes: row {i} has a bad number: {exc}") from exc
        rows.append({"parcel": parcel, "street": street, "city": _norm(r.get("city")) or bap.DEFAULT_CITY,
                     "zip": _norm(r.get("zip")), "year": year, "units": max(units, 1),
                     "lat": None, "lng": None})
    return rows


def read_centroids(path: str = CENTROIDS_CSV) -> dict[str, tuple[float, float]]:
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return {r["parcel"]: (float(r["lat"]), float(r["lng"])) for r in csv.DictReader(fh)}


def geocode(rows: list[dict], centroids: dict[str, tuple[float, float]] | None = None) -> int:
    """Parcel centroid first (exact lot), Census geocoder for the rest. Returns the centroid count."""
    hit = 0
    for i, r in enumerate(rows):
        r.update({"id": str(i), "state": bap.DEFAULT_STATE})
        c = (centroids or {}).get(r.get("parcel", ""))
        if c:
            r["lat"], r["lng"] = c
            hit += 1
    cache = bap._load_cache()
    bap.geocode_batch([r for r in rows if r["lat"] is None and r["street"]], cache)
    return hit


def band_color(year: int, build_year: int) -> str:
    age = build_year - year
    if age <= 1:
        return BAND_COLORS[0]
    if age <= 3:
        return BAND_COLORS[1]
    if age <= 6:
        return BAND_COLORS[2]
    return BAND_COLORS[3]


def build(rows: list[dict], rings: list[list], build_year: int) -> tuple[dict, int, int]:
    """Point features for geocoded, in-city permits, newest first. One pin per
    address-year (a subdivision phase can issue several permits at one address)."""
    merged: dict[tuple[str, int], dict] = {}
    nocoord = outside = 0
    for r in rows:
        if r["lat"] is None or r["lng"] is None:
            nocoord += 1
            continue
        if not bap.in_city(r["lng"], r["lat"], rings):
            outside += 1
            continue
        key = (r.get("parcel") or r["street"].upper(), r["year"])
        if key in merged:
            merged[key]["units"] += r["units"]
            merged[key]["permits"] += 1
        else:
            merged[key] = dict(r, permits=1)
    features = []
    for r in sorted(merged.values(), key=lambda r: (-r["year"], r["street"])):
        rows_ = [["New-home permit issued", str(r["year"])]]
        if r["units"] > 1 or r["permits"] > 1:
            rows_.append(["Homes permitted here", f"{r['units']} ({r['permits']} permits)"])
        rows_.append(["Note", "A permit is permission to build, not proof the home was finished"])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(r["lng"], 6), round(r["lat"], 6)]},
            "properties": {
                "name": bap.titlecase_street(r["street"]) or "New home",
                "year": r["year"],
                "units": r["units"],
                "_color": band_color(r["year"], build_year),
                "_radius": 6,
                "_popupRows": rows_,
            },
        })
    return {"type": "FeatureCollection", "features": features}, nocoord, outside


def main() -> int:
    rows = read_rows()
    print(f"Read {len(rows)} new-home permits from {os.path.basename(SOURCE_CSV)}")
    hit = geocode(rows, read_centroids())
    print(f"  {hit} permits placed from parcel centroids, the rest geocoded by address")
    fc, nocoord, outside = build(rows, bap._rings_from_boundary(), date.today().year)
    write_geojson(OUT, fc)
    years = Counter(f["properties"]["year"] for f in fc["features"])
    print(f"Wrote {len(fc['features'])} pins -> {os.path.basename(OUT)} "
          f"(dropped {nocoord} un-geocoded, {outside} outside city); by year: "
          + ", ".join(f"{y}: {n}" for y, n in sorted(years.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
