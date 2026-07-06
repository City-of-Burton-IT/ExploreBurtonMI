# Build public/precincts.geojson: the City of Burton voting precincts, as a map
# overlay layer ("which precinct am I in").
#
# Source: State of Michigan "2024 Voting Precincts" open data (Secretary of State),
# served from the State ArcGIS REST endpoint. Public, redistributable. Only the
# precinct boundary + number/name are kept: the dataset's Registered_Voters /
# Active_Voters count fields are deliberately EXCLUDED (the map answers "which
# precinct", not "how many voters"). Pairs with the Elections guide section's MVIC
# polling-place lookup.
#
# Re-runnable (bump --year when the SOS publishes a newer precinct set):
#     python tools/extract_precincts.py [--year 2024]
from __future__ import annotations

import argparse
import os
import sys

from lib.geo import round_coords
from lib.httpio import get_json
from lib.iox import write_geojson
from lib.paths import public_path

OUT = public_path("precincts.geojson")
# State of Michigan OpenData boundaries MapServer; layer 9 = 2024 Voting Precincts.
SERVICE = "https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/boundaries/MapServer/9/query"
JURISDICTION = "Burton"
COUNTY_FIPS = "049"  # Genesee


def fetch(year: int) -> list:
    params = {
        "where": f"Jurisdiction_Name='{JURISDICTION}' AND COUNTYFIPS='{COUNTY_FIPS}'",
        "outFields": "PRECINCT,Precinct_Long_Name,ELECTIONYE",
        "outSR": "4326",
        "f": "geojson",
    }
    fc = get_json(SERVICE, params, timeout=40)
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
            "geometry": {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])},
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
    write_geojson(OUT, fc)
    print(f"Wrote {OUT}")
    print(f"  {len(features)} Burton precincts ({args.year}):")
    for f in features:
        print(f"    Precinct {f['properties']['precinct']}")
    print(f"  file size: {os.path.getsize(OUT) // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
