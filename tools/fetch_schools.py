# Build public/info-schools.json: a Schools dashboard for the public school
# districts that serve the City of Burton.
#
# IMPORTANT framing: this panel is deliberately PER-DISTRICT, never summed.
# Four of the seven districts (Carman-Ainsworth, Davison, Grand Blanc, Kearsley)
# only clip Burton; most of their students live and attend school outside the
# city. CCD reports whole-district enrollment with no way to apportion the Burton
# slice, so any total / aggregate demographic figure would read as a "Burton"
# number while actually being a multi-district number. We therefore publish only:
#   - a plain count of districts serving Burton,
#   - per-district enrollment bars (each district its own bar, no sum),
#   - a per-district link out, and
#   - a visible note that several districts extend well beyond city limits.
#
# Data: Urban Institute Education Data API (educationdata.urban.org), which wraps
# the NCES Common Core of Data (CCD). LEAID == the Census unsd GEOID, so the 7
# district IDs are read straight from public/school-districts.geojson (no
# hard-coded list). The API is occasionally flaky for larger districts (522 /
# timeout), so each fetch retries with backoff and falls back to the grade-99
# enrollment endpoint when directory.enrollment is null.
#
# Re-runnable annually (committed output; the site reads the JSON, never the API):
#     python tools/fetch_schools.py [--year 2023]
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DISTRICTS_GEOJSON = os.path.join(ROOT, "public", "school-districts.geojson")
OUT = os.path.join(ROOT, "public", "info-schools.json")

API = "https://educationdata.urban.org/api/v1/school-districts/ccd"

# Verified official district websites (curl -L 200, 2026-06-05), keyed by LEAID.
DISTRICT_URLS = {
    "2603540": "https://www.athertonschools.org/",
    "2604740": "https://bendleschools.org/",
    "2604800": "https://www.bentleyschools.org/",
    "2607890": "https://www.carman.k12.mi.us/",
    "2611430": "https://www.davisonschools.org/",
    "2616350": "https://www.gbcs.org/",
    "2620070": "https://www.kearsleyschools.org/",
}


def _get(url: str, attempts: int = 4) -> dict:
    """GET JSON with retry/backoff, the Urban API 522s/times out under load."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30 + i * 20) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 - transient; retry then give up
            last = exc
            if i < attempts - 1:
                time.sleep(2 + i * 2)
    raise RuntimeError(f"all {attempts} attempts failed for {url}: {last}")


def load_districts() -> list[dict]:
    """[{leaid, name}] read from the committed school-districts overlay."""
    with open(DISTRICTS_GEOJSON, "r", encoding="utf-8") as fh:
        fc = json.load(fh)
    out = []
    for f in fc.get("features", []):
        p = f.get("properties", {})
        leaid = str(p.get("geoid", "")).strip()
        name = p.get("name", "").strip()
        if leaid and name:
            out.append({"leaid": leaid, "name": name})
    if not out:
        raise SystemExit(f"No districts found in {DISTRICTS_GEOJSON}")
    return out


def enrollment_for(leaid: str, year: int) -> int | None:
    """Whole-district enrollment for one LEAID; None if unavailable.

    Primary source is the CCD directory's `enrollment` field; when that is null
    we fall back to summing the grade-99 (all grades) / race-99 / sex-99 total
    from the enrollment endpoint.
    """
    try:
        d = _get(f"{API}/directory/{year}/?leaid={leaid}")
        rows = d.get("results", [])
        if rows and rows[0].get("enrollment") not in (None, ""):
            return int(rows[0]["enrollment"])
    except Exception as exc:  # noqa: BLE001 - try the fallback before failing
        print(f"    directory failed for {leaid} ({exc}); trying enrollment endpoint")

    try:
        e = _get(f"{API}/enrollment/{year}/grade-99/?leaid={leaid}")
        for r in e.get("results", []):
            if r.get("race") == 99 and r.get("sex") == 99:
                val = r.get("enrollment")
                if val not in (None, "") and int(val) >= 0:
                    return int(val)
    except Exception as exc:  # noqa: BLE001
        print(f"    enrollment endpoint failed for {leaid} ({exc})")
    return None


def build_panel(districts: list[dict], year: int) -> dict:
    series = []
    links = []
    missing = []
    for d in districts:
        enr = enrollment_for(d["leaid"], year)
        # Trim the long suffixes so the bar labels stay readable.
        short = (
            d["name"]
            .replace(" Community School District", "")
            .replace(" Community Schools", "")
            .replace(" Public Schools", "")
        )
        print(f"    {short:20} {enr if enr is not None else 'n/a'}")
        if enr is not None:
            series.append({"label": short, "value": enr})
        else:
            missing.append(short)
        url = DISTRICT_URLS.get(d["leaid"])
        if url:
            links.append({"text": short, "href": url})

    series.sort(key=lambda s: s["value"], reverse=True)

    # Education levels (attainment) live on the Demographics dashboard -- link to
    # them rather than duplicate the chart. Add the colleges that serve the area
    # (issue #22, higher education).
    links.append({"text": "Education levels (Demographics)", "href": "#demographics"})
    for name, url in (
        ("Mott Community College", "https://www.mcc.edu"),
        ("University of Michigan-Flint", "https://www.umflint.edu"),
        ("Kettering University", "https://www.kettering.edu"),
        ("Baker College", "https://www.baker.edu"),
    ):
        links.append({"text": name, "href": url})

    notes = [
        "Several of these districts extend well beyond Burton's city limits: "
        "enrollment shown is each district's total, not the number of Burton "
        "residents it serves. Use the Map's \"School districts\" layer to see which "
        "district covers an address.",
        "Adults' education levels (high-school and college attainment) for Burton "
        "are on the Demographics dashboard. Colleges serving the area include Mott "
        "Community College, the University of Michigan-Flint, Kettering University, "
        "and Baker College.",
        "Source: Urban Institute Education Data API, which republishes the U.S. "
        "Department of Education's National Center for Education Statistics (NCES) "
        "Common Core of Data.",
    ]
    if missing:
        notes.insert(1, "Enrollment was unavailable for: " + ", ".join(missing) + ".")

    return {
        "title": "Burton Schools",
        "subtitle": f"Public school districts serving the City of Burton ({year})",
        "stats": [
            {
                "label": "Districts serving Burton",
                "value": str(len(districts)),
                "hint": "public school districts",
            },
        ],
        "charts": [
            {
                "type": "bars",
                "title": f"Enrollment by district ({year})",
                "series": series,
            },
        ],
        "source": f"NCES Common Core of Data {year}, via the Urban Institute Education Data API",
        "links": links,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Burton Schools dashboard JSON.")
    parser.add_argument("--year", type=int, default=2023, help="CCD school year (default 2023)")
    args = parser.parse_args()

    districts = load_districts()
    print(f"  {len(districts)} districts; fetching enrollment for {args.year} ...")
    panel = build_panel(districts, args.year)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(panel, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OUT}")
    print(f"  districts charted: {len(panel['charts'][0]['series'])}  links: {len(panel['links'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
