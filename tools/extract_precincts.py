# Build public/precincts.geojson: the City of Burton voting precincts, as a map
# overlay layer ("which precinct am I in").
#
# Source: State of Michigan "2024 Voting Precincts" open data (Secretary of State),
# served from the State ArcGIS REST endpoint. Public, redistributable. Only the
# precinct boundary + number/name are kept -- the dataset's Registered_Voters /
# Active_Voters count fields are deliberately EXCLUDED (the map answers "which
# precinct", not "how many voters"). Pairs with the Elections guide section's MVIC
# polling-place lookup.
#
# Re-runnable (bump --year when the SOS publishes a newer precinct set):
#     python tools/extract_precincts.py [--year 2024]
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "public", "precincts.geojson")
# State of Michigan OpenData boundaries MapServer; layer 9 = 2024 Voting Precincts.
SERVICE = "https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/boundaries/MapServer/9/query"
JURISDICTION = "Burton"
COUNTY_FIPS = "049"  # Genesee


def _round(coords, ndigits=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], ndigits), round(coords[1], ndigits)]
    return [_round(c, ndigits) for c in coords]


def fetch(year: int) -> list:
    params = {
        "where": f"Jurisdiction_Name='{JURISDICTION}' AND COUNTYFIPS='{COUNTY_FIPS}'",
        "outFields": "PRECINCT,Precinct_Long_Name,ELECTIONYE",
        "outSR": "4326",
        "f": "geojson",
    }
    url = SERVICE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        fc = json.load(resp)
    feats = fc.get("features", [])
    if not feats:
        raise SystemExit(f"No Burton precincts returned (check the service / year {year}).")
    return feats


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Burton voting-precinct overlay.")
    parser.add_argument("--year", type=int, default=2024, help="Precinct vintage label (default 2024)")
    args = parser.parse_args()

    raw = fetch(args.year)
    features = []
    for f in raw:
        p = f.get("properties", {})
        num = str(p.get("PRECINCT", "")).lstrip("0") or str(p.get("PRECINCT", ""))
        long_name = p.get("Precinct_Long_Name") or f"City of Burton, Precinct {num}"
        geom = f.get("geometry")
        if not geom:
            continue
        features.append({
            "type": "Feature",
            "properties": {"name": long_name, "precinct": num},
            "geometry": {"type": geom["type"], "coordinates": _round(geom["coordinates"])},
        })

    features.sort(key=lambda f: int(f["properties"]["precinct"]) if f["properties"]["precinct"].isdigit() else 0)
    fc = {
        "type": "FeatureCollection",
        "_source": (
            f"State of Michigan {args.year} Voting Precincts (Secretary of State), open data. "
            "City of Burton precincts only; boundary + precinct number/name (no voter counts)."
        ),
        "features": features,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  {len(features)} Burton precincts ({args.year}):")
    for f in features:
        print(f"    Precinct {f['properties']['precinct']}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
