# Build public/info-water.json for the Drinking Water dashboard.
#
# Source: US EPA Safe Drinking Water Information System (SDWIS) via the public
# Envirofacts REST service (https://data.epa.gov/efservice/) -- keyless, public
# domain. Burton's community water system is PWSID MI0001010 ("BURTON, CITY OF").
#
# This is a *compliance* snapshot, framed honestly: it distinguishes health-based
# violations from monitoring/reporting (paperwork) violations, and notes whether
# any remain open. No PII -- it's public infrastructure-compliance data.
#
# Re-runnable (committed output; the site reads the JSON, never EPA):
#   python tools/fetch_water.py
#
# Stdlib only (urllib), matching the other tools/ fetchers.
from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections import defaultdict

PWSID = "MI0001010"
EF = "https://data.epa.gov/efservice"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "info-water.json"))

# SDWIS violation category codes -> resident-friendly labels.
CATEGORY_LABELS = {
    "MCL": "Contaminant level (health)",
    "MRDL": "Disinfectant level (health)",
    "TT": "Treatment technique",
    "MR": "Monitoring & reporting",
    "RPT": "Reporting",
    "MON": "Monitoring",
    "Other": "Other",
}
SOURCE_LABELS = {
    "SW": "Surface water", "GW": "Groundwater",
    "SWP": "Surface water (purchased)", "GWP": "Groundwater (purchased)",
    "GU": "Groundwater under surface influence",
}


LEAD_AL = 0.015  # EPA lead action level (90th-percentile), mg/L


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_lead():
    """Latest Lead & Copper Rule 90th-percentile LEAD result (PB90) for Burton, with
    the monitoring-period range and the peak across periods. Copper (CU90) is not
    reported for Burton in SDWIS, so it is omitted rather than shown as missing."""
    try:
        samples = {s["sample_id"]: s for s in _get(f"{EF}/LCR_SAMPLE/PWSID/{PWSID}/JSON")}
        results = _get(f"{EF}/LCR_SAMPLE_RESULT/PWSID/{PWSID}/JSON")
    except Exception:
        return None
    lead = []
    for r in results:
        if r.get("contaminant_code") != "PB90":
            continue
        end = (samples.get(r.get("sample_id"), {}).get("sampling_end_date") or "")[:10]
        try:
            lead.append((end, float(r.get("sample_measure")), r.get("unit_of_measure") or "mg/L"))
        except (TypeError, ValueError):
            continue
    if not lead:
        return None
    lead.sort()
    date, value, unit = lead[-1]
    return {"value": value, "unit": unit, "last_year": date[:4],
            "first_year": lead[0][0][:4], "periods": len(lead),
            "peak": max(v for _, v, _ in lead)}


def main() -> None:
    ws = _get(f"{EF}/WATER_SYSTEM/PWSID/{PWSID}/JSON")
    if not ws:
        sys.exit(f"No WATER_SYSTEM record for {PWSID}")
    w = ws[0]
    pop = int(w.get("population_served_count") or 0)
    conns = int(w.get("service_connections_count") or 0)
    source = SOURCE_LABELS.get(w.get("primary_source_code") or w.get("gw_sw_code"),
                               w.get("gw_sw_code") or "Public supply")

    viols = _get(f"{EF}/VIOLATION/PWSID/{PWSID}/JSON")
    by_year: dict[str, int] = defaultdict(int)
    by_cat: dict[str, int] = defaultdict(int)
    health = open_count = 0
    for v in viols:
        yr = (v.get("compl_per_begin_date") or "")[:4]
        if yr:
            by_year[yr] += 1
        by_cat[CATEGORY_LABELS.get(v.get("violation_category_code"),
                                   v.get("violation_category_code") or "Other")] += 1
        if (v.get("is_health_based_ind") or "").upper() == "Y":
            health += 1
        # compliance_status_code: 'R'/'K' resolved, 'O' open/unaddressed
        if (v.get("compliance_status_code") or "").upper() == "O":
            open_count += 1

    total = len(viols)
    first_year = min((y for y in by_year), default=None)

    stats = [
        {"label": "Residents served", "value": f"{pop:,}", "hint": "EPA SDWIS"},
        {"label": "Service connections", "value": f"{conns:,}"},
        {"label": "Water source", "value": source},
        {"label": "Open health violations", "value": f"{open_count}",
         "hint": "currently unresolved"},
        {"label": "Health-based violations", "value": f"{health}",
         "hint": f"on record{f' since {first_year}' if first_year else ''}"},
        {"label": "Total violations on record", "value": f"{total}",
         "hint": "all resolved" if open_count == 0 else f"{open_count} open"},
    ]

    # Lead & Copper Rule: the 90th-percentile lead result -- a headline residents
    # (especially Flint-adjacent) care about. Shown prominently after the source.
    lead = fetch_lead()
    if lead:
        stats.insert(3, {
            "label": "Lead (90th percentile)",
            "value": f"{lead['value']:g} {lead['unit']}",
            "hint": f"EPA action level {LEAD_AL:g}; tested {lead['last_year']}",
        })

    charts = []
    if by_cat:
        charts.append({
            "type": "bars", "title": "Violations by type (on record)", "unit": "",
            "series": sorted(({"label": k, "value": v} for k, v in by_cat.items()),
                             key=lambda s: -s["value"]),
        })
    if by_year:
        years = sorted(by_year)
        charts.append({
            "type": "trend", "title": "Violations by year", "unit": "",
            "points": [{"x": y, "y": by_year[y]} for y in years],
        })

    notes = [
        "\"Violations\" includes both health-based exceedances and "
        "monitoring/reporting (paperwork) requirements; most are the latter. "
        "A monitoring/reporting violation does not mean the water was unsafe.",
        "Counts are everything on record in EPA SDWIS"
        + (f" (since {first_year})" if first_year else "")
        + (". No violations are currently open." if open_count == 0 else "."),
        "Source: US EPA Safe Drinking Water Information System via the public "
        "Envirofacts service. This product is not endorsed or certified by the EPA.",
    ]
    if lead:
        v = lead["value"]
        level = (f"at or below the detection limit (reported {v:g} {lead['unit']})"
                 if v == 0 else f"{v:g} {lead['unit']}")
        rel = "well below" if lead["peak"] < LEAD_AL else "against"
        notes.insert(0,
            f"Under the federal Lead & Copper Rule, Burton's 90th-percentile lead result "
            f"has been {level} -- {rel} the EPA action level of {LEAD_AL:g} {lead['unit']} -- "
            f"every monitoring period on record ({lead['first_year']}-{lead['last_year']}). "
            f"Copper is monitored but not separately reported for Burton in SDWIS.")

    panel = {
        "title": "Drinking Water",
        "subtitle": "Burton's public water system -- EPA compliance snapshot",
        "stats": stats,
        "charts": charts,
        "source": f"US EPA Safe Drinking Water Information System (SDWIS), "
                  f"public water system {PWSID} (City of Burton).",
        "links": [
            {"text": "EPA drinking-water data (ECHO)",
             "href": f"https://echodata.epa.gov/echo/sdw_report.get_report?pgm_sys_id_in={PWSID}"},
        ],
        "notes": notes,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT}")
    print(f"  pop={pop:,} conns={conns:,} source={source}")
    print(f"  lead(90th): {lead}")
    print(f"  violations: total={total} health-based={health} open={open_count}")
    print(f"  by year: {dict(sorted(by_year.items()))}")
    print(f"  by category: {dict(by_cat)}")


if __name__ == "__main__":
    main()
