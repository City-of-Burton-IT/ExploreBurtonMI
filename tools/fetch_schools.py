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

from lib.httpio import get_json
from lib.iox import write_json
from lib.paths import public_path

DISTRICTS_GEOJSON = public_path("school-districts.geojson")
OUT = public_path("info-schools.json")

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


# --- Census ACS attainment (citywide adults 25+) ---------------------------------
# Educational attainment + the bachelor's-degree comparison live here (moved from
# Demographics) so the education story sits with the schools.
CENSUS_STATE, CENSUS_PLACE, CENSUS_COUNTY = "26", "12060", "049"
BACHELOR_CODES = ["022", "023", "024", "025"]
EDU_GROUPS = [
    ("No diploma", [f"{n:03d}" for n in range(2, 17)]),
    ("High school / GED", ["017", "018"]),
    ("Some college / associate", ["019", "020", "021"]),
    ("Bachelor's degree", ["022"]),
    ("Graduate / professional", ["023", "024", "025"]),
]
EDU_TREND_YEARS = [2013, 2018, 2023]


def _census_row(year: int, get_vars: list[str], geo: str, key: str) -> dict:
    url = (f"https://api.census.gov/data/{year}/acs/acs5"
           f"?get={','.join(get_vars)}&{geo}&key={key}")
    rows = get_json(url, timeout=40)
    return dict(zip(rows[0], rows[1]))


def _cint(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# Cumulative attainment levels for the Burton/county/state comparison (each is the
# share of adults 25+ at OR ABOVE that level).
EDU_LEVELS = [
    ("High school or higher", [f"{n:03d}" for n in range(17, 26)]),
    ("Some college or higher", [f"{n:03d}" for n in range(19, 26)]),
    ("Bachelor's or higher", ["022", "023", "024", "025"]),
    ("Graduate / professional", ["023", "024", "025"]),
]
ALL_EDU_VARS = [f"B15003_{n:03d}E" for n in range(1, 26)]


def _level_pct(rec: dict, codes: list[str]) -> int:
    total = _cint(rec.get("B15003_001E"))
    return round(sum(_cint(rec.get(f"B15003_{c}E")) for c in codes) / total * 100) if total else 0


def build_education(key: str | None, year: int = 2023) -> dict | None:
    """Citywide educational attainment (ACS B15003): attainment bars, a Burton vs.
    county vs. state comparison across all levels, and a bachelor's trend.
    Returns None if no key."""
    if not key:
        print("  (no Census key -- skipping education attainment)")
        return None
    place_geo = f"for=place:{CENSUS_PLACE}&in=state:{CENSUS_STATE}"
    geos = [
        ("Burton", place_geo),
        ("Genesee County", f"for=county:{CENSUS_COUNTY}&in=state:{CENSUS_STATE}"),
        ("Michigan", f"for=state:{CENSUS_STATE}"),
    ]
    recs: dict[str, dict] = {}
    for name, geo in geos:
        try:
            recs[name] = _census_row(year, ALL_EDU_VARS, geo, key)
        except Exception as exc:  # noqa: BLE001
            print(f"  education fetch {name} failed ({exc})")
    if "Burton" not in recs:
        return None

    bars = [{"label": lbl, "value": sum(_cint(recs["Burton"].get(f"B15003_{c}E")) for c in codes)}
            for lbl, codes in EDU_GROUPS]
    compare = []
    for label, codes in EDU_LEVELS:
        vals = [{"name": name, "value": _level_pct(recs[name], codes)} for name, _ in geos if name in recs]
        if len(vals) >= 2:
            compare.append({"label": label, "unit": "%", "values": vals})

    bach_codes = ["022", "023", "024", "025"]
    trend = []
    for yr in EDU_TREND_YEARS:
        try:
            p = _level_pct(_census_row(yr, ["B15003_001E", *(f"B15003_{c}E" for c in bach_codes)], place_geo, key), bach_codes)
            if p > 0:
                trend.append({"x": str(yr), "y": p})
        except Exception as exc:  # noqa: BLE001
            print(f"  bachelor's trend {yr} skipped ({exc})")
    return {"bars": bars, "bach_pct": _level_pct(recs["Burton"], bach_codes),
            "compare_rows": compare, "trend": trend}


def _get(url: str, attempts: int = 4) -> dict:
    """GET JSON with retry/backoff, the Urban API 522s/times out under load.

    Thin wrapper over lib.httpio.get_json (which this retry logic was promoted
    into), kept as a module-level seam so tests can stub the API."""
    return get_json(url, attempts=attempts, timeout=30)


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


def district_stats(leaid: str, year: int) -> tuple[int | None, float | None]:
    """(enrollment, teachers_total_fte) for one LEAID; either may be None.

    Both come from the CCD directory in a single call. When the directory's
    `enrollment` is null we fall back to the grade-99 (all grades) / race-99 /
    sex-99 total from the enrollment endpoint; teacher FTE is directory-only.
    """
    enr: int | None = None
    teachers: float | None = None
    try:
        d = _get(f"{API}/directory/{year}/?leaid={leaid}")
        rows = d.get("results", [])
        if rows:
            t = rows[0].get("teachers_total_fte")
            if t not in (None, "", 0):
                teachers = float(t)
            e = rows[0].get("enrollment")
            if e not in (None, ""):
                enr = int(e)
    except Exception as exc:  # noqa: BLE001 - try the fallback before failing
        print(f"    directory failed for {leaid} ({exc}); trying enrollment endpoint")

    if enr is None:
        try:
            e = _get(f"{API}/enrollment/{year}/grade-99/?leaid={leaid}")
            for r in e.get("results", []):
                if r.get("race") == 99 and r.get("sex") == 99:
                    val = r.get("enrollment")
                    if val not in (None, "") and int(val) >= 0:
                        enr = int(val)
                        break
        except Exception as exc:  # noqa: BLE001
            print(f"    enrollment endpoint failed for {leaid} ({exc})")
    return enr, teachers


def build_panel(districts: list[dict], year: int, edu: dict | None = None) -> dict:
    series = []
    ratio_series = []
    links = []
    missing = []
    for d in districts:
        enr, teachers = district_stats(d["leaid"], year)
        # Trim the long suffixes so the bar labels stay readable.
        short = (
            d["name"]
            .replace(" Community School District", "")
            .replace(" Community Schools", "")
            .replace(" Public Schools", "")
        )
        print(f"    {short:20} {enr if enr is not None else 'n/a'}"
              f"  teachers={teachers if teachers else 'n/a'}")
        if enr is not None:
            series.append({"label": short, "value": enr})
        else:
            missing.append(short)
        if enr is not None and teachers:
            ratio_series.append({"label": short, "value": round(enr / teachers, 1)})
        url = DISTRICT_URLS.get(d["leaid"])
        if url:
            links.append({"text": short, "href": url})

    series.sort(key=lambda s: s["value"], reverse=True)
    ratio_series.sort(key=lambda s: s["value"])

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

    stats = [
        {"label": "Districts serving Burton", "value": str(len(districts)),
         "hint": "public school districts"},
    ]
    charts = [
        {"type": "bars", "title": f"Enrollment by district ({year})", "series": series},
    ]
    if len(ratio_series) >= 2:
        charts.append({"type": "bars", "title": f"Students per teacher by district ({year})",
                       "unit": "", "series": ratio_series})
    source = f"NCES Common Core of Data {year}, via the Urban Institute Education Data API"

    # Citywide adult educational attainment (Census), moved here from Demographics.
    if edu:
        stats.append({"label": "Bachelor's degree or higher", "value": f"{edu['bach_pct']}%",
                      "hint": "Burton adults 25+, citywide"})
        charts.append({"type": "bars", "title": "Adults' education levels (citywide, age 25+)",
                       "unit": "", "series": edu["bars"]})
        if len(edu.get("trend", [])) >= 2:
            charts.append({"type": "trend", "title": "Bachelor's degree or higher (% age 25+)",
                           "unit": "%", "points": edu["trend"]})
        if len(edu.get("compare_rows", [])) >= 2:
            charts.append({"type": "compare",
                           "title": "Education levels: Burton vs. county & state",
                           "rows": edu["compare_rows"]})
        source += "; U.S. Census ACS 5-year (educational attainment)"
        notes.append(
            "Educational attainment is for Burton adults age 25+ citywide (U.S. Census ACS) "
            "-- residents' own completed education, separate from the per-district K-12 "
            "enrollment shown above.")

    return {
        "title": "Burton Schools",
        "subtitle": f"Public school districts serving the City of Burton ({year})",
        "stats": stats,
        "charts": charts,
        "source": source,
        "links": links,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Burton Schools dashboard JSON.")
    parser.add_argument("--year", type=int, default=2023, help="CCD school year (default 2023)")
    parser.add_argument("--census-key", default=os.environ.get("CENSUS_API_KEY"),
                        help="Census API key for citywide education attainment (or set CENSUS_API_KEY)")
    args = parser.parse_args()

    districts = load_districts()
    print(f"  {len(districts)} districts; fetching enrollment for {args.year} ...")
    edu = build_education(args.census_key)
    panel = build_panel(districts, args.year, edu)
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(f"  districts charted: {len(panel['charts'][0]['series'])}  links: {len(panel['links'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
