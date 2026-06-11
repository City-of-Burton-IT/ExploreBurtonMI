"""Build public/fire-stations.geojson for the "Fire call volume (by station)" map
overlay: one proportional circle at each Burton fire station, sized by that station
area's latest-year call volume.

PII-safe by construction: it uses only AGGREGATE station counts (from the Public
Safety dashboard's "Calls by station area" chart) and the PUBLIC station addresses
(the curated facilities in data.geojson). No incident locations.

The radius is ABSOLUTELY proportional to sqrt(calls) (area-proportional symbols),
so a station with 4x the calls draws 2x the radius -- an honest visual.

Re-runnable (committed output; the site reads the geojson, never the network):
    python tools/build_fire_stations.py

Stdlib only (json, math).
"""
from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INFO = os.path.join(ROOT, "public", "info-publicsafety.json")
PLACES = os.path.join(ROOT, "public", "data.geojson")
OUT = os.path.join(ROOT, "public", "fire-stations.geojson")

MAX_R = 24.0   # px radius of the busiest station
MIN_R = 6.0    # never draw smaller than this
COLOR = "#c62828"  # fire red; size carries the magnitude


def station_counts(info: dict) -> dict[int, dict]:
    """{station_number: {'calls': int, 'year': str}} from the by-station chart."""
    chart = next(
        (c for c in info.get("charts", [])
         if c.get("type") == "compare" and "station area" in c.get("title", "").lower()),
        None,
    )
    if not chart:
        raise SystemExit("ERROR: no 'Calls by station area' chart in info-publicsafety.json")
    out: dict[int, dict] = {}
    for row in chart.get("rows", []):
        label = row.get("label", "")  # e.g. "Station 1 area"
        num = next((int(t) for t in label.split() if t.isdigit()), None)
        if num is None:
            continue
        # latest year = the highest numeric year name among the row values
        latest = max(row["values"], key=lambda v: int(v["name"]))
        out[num] = {"calls": int(latest["value"]), "year": latest["name"]}
    return out


def station_coords(places: dict) -> dict[int, list]:
    """{station_number: [lon, lat]} from curated 'Burton Fire Station N' facilities."""
    out: dict[int, list] = {}
    for f in places.get("features", []):
        name = (f.get("properties", {}) or {}).get("name", "") or ""
        if "fire station" in name.lower():
            num = next((int(t) for t in name.replace("(", " ").split() if t.isdigit()), None)
            if num is not None and f.get("geometry", {}).get("type") == "Point":
                out[num] = f["geometry"]["coordinates"]
    return out


def build(counts: dict[int, dict], coords: dict[int, list]) -> dict:
    stations = sorted(set(counts) & set(coords))
    if not stations:
        raise SystemExit("ERROR: no station matched between counts and coordinates")
    max_calls = max(counts[n]["calls"] for n in stations) or 1

    features = []
    for n in stations:
        calls = counts[n]["calls"]
        radius = round(max(MIN_R, MAX_R * math.sqrt(calls / max_calls)), 1)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coords[n]},
            "properties": {
                "station": f"Station {n}",
                "calls": calls,
                "year": counts[n]["year"],
                "_radius": radius,
                "_color": COLOR,
                "_popupRows": [
                    [f"Calls for service ({counts[n]['year']})", f"{calls:,}"],
                    ["Coverage", f"Station {n} response area"],
                ],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def main() -> int:
    with open(INFO, encoding="utf-8") as fh:
        info = json.load(fh)
    with open(PLACES, encoding="utf-8") as fh:
        places = json.load(fh)

    counts = station_counts(info)
    coords = station_coords(places)
    fc = build(counts, coords)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    for f in fc["features"]:
        p = f["properties"]
        print(f"  {p['station']}: {p['calls']} calls ({p['year']}) -> r={p['_radius']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
