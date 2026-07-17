# Build public/address-points.json: a compact, city-owned address lookup table
# used for ON-DEVICE reverse-geocode of a dropped "Report an issue" pin (#71).
#
# WHY THIS EXISTS / PRIVACY: the public site is static with no backend, and we
# will not send a resident's dropped-pin coordinates to a third-party geocoder.
# Instead we ship a committed table of [lat, lng, address] for every addressable
# point in the city; the app does a nearest-neighbour lookup entirely on-device
# (src/lib/reverseGeocode.ts). The table is city-owned data, so it is clean to
# publish under ADR-0002 (unlike vendor address data).
#
# SOURCE: a Burton Assessing address export (parcel + site address), dropped at
# pipeline/data/address-points-source.csv. Most Assessing exports carry the
# street address but NOT coordinates, so we forward-geocode once, at build time,
# via the free US Census BATCH geocoder (public-domain, no key, <=10k rows per
# request). Build-time forward-geocoding sidesteps the Census reverse limitation
# (reverse returns geographies, not street addresses) -- we go address -> coords
# here and do coords -> nearest address in the browser.
#
# The source CSV is produced (internally) by C:\utils\Extract-BurtonAddressPoints.ps1,
# which reads the BS&A Assessing roll via the read-only bsa_readonly SQL login. That
# extract is NOT in this public repo (it names the internal SQL server); only this
# generic builder and the committed output JSON are public.
#
# Re-runnable (committed output; the site reads the JSON, never the geocoder):
#     # run with the pipeline venv (has `requests`):
#     pipeline/.venv/Scripts/python tools/build_address_points.py
#
# Refresh recipe: re-run the internal extract to refresh pipeline/data/
# address-points-source.csv, re-run this script, commit public/address-points.json.
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time

import requests

from lib.iox import write_geojson
from lib.paths import REPO_ROOT as ROOT
from lib.paths import pipeline_data_path, public_path
from lib.shapecheck import assert_shape

SOURCE_CSV = pipeline_data_path("address-points-source.csv")
BOUNDARY = public_path("boundary.geojson")
OUT_JSON = public_path("address-points.json")
CACHE = pipeline_data_path("cache", "address_geocode.json")

# --- Source column mapping ----------------------------------------------------
# The internal extract aliases the BS&A columns to these clean headers
# (parcel, street, city, state, zip). Either set COLUMN_ADDRESS to a single
# combined-line column, OR the separate street/city/state/zip columns.
COLUMN_ADDRESS = None  # a single combined line, if the source has one
COLUMN_STREET = "street"  # e.g. "1001 S CENTER RD" (BS&A propstreetcombined)
COLUMN_CITY = "city"  # postal city (Burton/Flint/Grand Blanc) -- kept for geocoding
COLUMN_STATE = "state"
COLUMN_ZIP = "zip"
# Optional pre-existing coordinates (if the source already has them, we skip the
# geocoder for that row). The Assessing roll has none, so these stay None.
COLUMN_LAT = None
COLUMN_LNG = None

DEFAULT_CITY = "Burton"
DEFAULT_STATE = "MI"

CENSUS_BATCH = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BENCHMARK = "Public_AR_Current"
CHUNK = 9000  # Census caps a batch at 10,000 rows; stay under it.
HTTP_TIMEOUT = 120


def _norm(s) -> str:
    return " ".join(str(s or "").split()).strip()


def _addr_key(street: str, city: str, state: str, zip_: str) -> str:
    return ", ".join(p for p in (street, city, state, zip_) if p)


def titlecase_street(street: str) -> str:
    """BS&A stores situs addresses in all-caps; present them mixed-case. Single
    letters (directionals N/S/E/W) stay upper; everything else title-cases."""
    parts = []
    for w in street.split():
        parts.append(w if len(w) == 1 else w.capitalize())
    return " ".join(parts)


def read_source_rows() -> list[dict]:
    """Parse the export into normalized rows: {id, street, city, state, zip,
    lat, lng}. lat/lng are floats when the export already has them, else None."""
    if not os.path.exists(SOURCE_CSV):
        sys.exit(
            f"Source export not found: {SOURCE_CSV}\n"
            "Drop a Burton Assessing address export there first (see header)."
        )
    rows: list[dict] = []
    with open(SOURCE_CSV, newline="", encoding="utf-8-sig") as fh:
        raw_rows = list(csv.DictReader(fh))
    # Fail loud if the extract's column aliases changed: a silently-missing
    # street column would otherwise skip every row and emit an empty table.
    required = [COLUMN_ADDRESS] if COLUMN_ADDRESS else [
        COLUMN_STREET, COLUMN_CITY, COLUMN_STATE, COLUMN_ZIP]
    assert_shape(raw_rows, required, "address-points source rows")
    for i, raw in enumerate(raw_rows):
        if COLUMN_ADDRESS:
            street = _norm(raw.get(COLUMN_ADDRESS))
            city = state = zip_ = ""
        else:
            street = _norm(raw.get(COLUMN_STREET))
            city = _norm(raw.get(COLUMN_CITY)) or DEFAULT_CITY
            state = _norm(raw.get(COLUMN_STATE)) or DEFAULT_STATE
            zip_ = _norm(raw.get(COLUMN_ZIP))
        if not street:
            continue
        lat = lng = None
        if COLUMN_LAT and COLUMN_LNG:
            try:
                lat = float(raw[COLUMN_LAT])
                lng = float(raw[COLUMN_LNG])
            except (KeyError, TypeError, ValueError):
                lat = lng = None
        rows.append(
            {"id": str(i), "street": street, "city": city, "state": state,
             "zip": zip_, "lat": lat, "lng": lng}
        )
    # Dedupe identical situs addresses (condos / lot splits share one street
    # address across many parcels) -- one lookup point per unique address.
    seen: set[str] = set()
    unique: list[dict] = []
    for r in rows:
        key = _addr_key(r["street"], r["city"], r["state"], r["zip"]).upper()
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def _load_cache() -> dict:
    return json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def _save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"))


def geocode_batch(rows: list[dict], cache: dict) -> None:
    """Fill row['lat']/['lng'] for rows lacking coordinates, via the Census batch
    geocoder, using the cache to skip already-resolved addresses. Mutates rows."""
    todo = []
    for r in rows:
        if r["lat"] is not None and r["lng"] is not None:
            continue
        key = _addr_key(r["street"], r["city"], r["state"], r["zip"])
        if key in cache:
            coord = cache[key]
            if coord:
                r["lat"], r["lng"] = coord[0], coord[1]
            continue
        todo.append(r)

    for start in range(0, len(todo), CHUNK):
        chunk = todo[start:start + CHUNK]
        buf = io.StringIO()
        w = csv.writer(buf)
        # Census batch format: Unique ID, Street, City, State, ZIP -- NO header.
        for r in chunk:
            w.writerow([r["id"], r["street"], r["city"], r["state"], r["zip"]])
        files = {"addressFile": ("addresses.csv", buf.getvalue(), "text/csv")}
        data = {"benchmark": BENCHMARK}
        print(f"  geocoding rows {start + 1}-{start + len(chunk)} of {len(todo)}...")
        resp = requests.post(CENSUS_BATCH, files=files, data=data, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        # Response is a header-less CSV: id, input, match, matchtype, matched,
        # "lon,lat", tigerlineid, side.
        for parsed in csv.reader(io.StringIO(resp.text)):
            # Match rows have 8 columns; No_Match/Tie rows have only 3
            # (id, input, indicator) -- record those as a miss, do not skip.
            if len(parsed) < 3:
                continue
            rid, match = parsed[0], parsed[2]
            row = next((x for x in chunk if x["id"] == rid), None)
            if row is None:
                continue
            key = _addr_key(row["street"], row["city"], row["state"], row["zip"])
            if match == "Match" and len(parsed) >= 6 and parsed[5]:
                lon, lat = parsed[5].split(",")
                row["lat"], row["lng"] = float(lat), float(lon)
                cache[key] = [float(lat), float(lon)]
            else:
                cache[key] = None
        _save_cache(cache)
        time.sleep(1)  # be polite to the Census service between chunks


# --- Clip to the city boundary (ray casting; stdlib) --------------------------
def _rings_from_boundary() -> list[list]:
    gj = json.load(open(BOUNDARY, encoding="utf-8"))
    feats = gj.get("features", [gj]) if gj.get("type") != "Feature" else [gj]
    rings: list[list] = []
    for f in feats:
        geom = f.get("geometry", f)
        gtype, coords = geom.get("type"), geom.get("coordinates", [])
        if gtype == "Polygon":
            rings.append(coords[0])
        elif gtype == "MultiPolygon":
            for poly in coords:
                rings.append(poly[0])
    return rings


def _in_ring(lng: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_city(lng: float, lat: float, rings: list[list]) -> bool:
    return any(_in_ring(lng, lat, r) for r in rings)


def main() -> int:
    rows = read_source_rows()
    print(f"Read {len(rows)} source rows from {os.path.basename(SOURCE_CSV)}")
    cache = _load_cache()
    geocode_batch(rows, cache)

    rings = _rings_from_boundary()
    points = []
    dropped_nocoord = dropped_outside = 0
    for r in rows:
        if r["lat"] is None or r["lng"] is None:
            dropped_nocoord += 1
            continue
        if not in_city(r["lng"], r["lat"], rings):
            dropped_outside += 1
            continue
        points.append([round(r["lat"], 6), round(r["lng"], 6), titlecase_street(r["street"])])

    # Stamp the date without Date.now-style nondeterminism concerns: build time.
    stamp = time.strftime("%Y-%m-%d")
    out = {"updated": stamp, "points": points}
    write_geojson(OUT_JSON, out, ensure_ascii=True)
    print(
        f"Wrote {len(points)} address points -> {os.path.relpath(OUT_JSON, ROOT)}\n"
        f"  dropped: {dropped_nocoord} un-geocoded, {dropped_outside} outside city"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
