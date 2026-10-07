"""Fetch FEMA NFIP flood-insurance aggregates for the City of Burton.

Source: OpenFEMA v3 NfipPolicies and NfipClaims (public, keyless; v2 is retired
2026-10-15). The datasets are redacted (no policyholder identity) and carry
latitude/longitude rounded to one decimal; this tool neither selects nor stores
coordinates or any row-level data. Only aggregates are written to
tools/data/nfip-burton.json, which is committed so the panel build is
reproducible offline.

    python tools/fetch_flood_insurance.py
"""
from __future__ import annotations

import datetime as dt
import os
import statistics
import sys

from lib.httpio import get_json
from lib.iox import write_json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "nfip-burton.json")
POLICIES_URL = "https://www.fema.gov/api/open/v3/NfipPolicies"
CLAIMS_URL = "https://www.fema.gov/api/open/v3/NfipClaims"
COMMUNITY_FILTER = "nfipCommunityName eq 'BURTON, CITY OF'"
PAGE = 1000
POLICY_FIELDS = (
    "policyCount,totalBuildingInsuranceCoverage,totalContentsInsuranceCoverage,"
    "totalInsurancePremiumOfThePolicy,policyEffectiveDate,policyTerminationDate,"
    "ratedFloodZone,occupancyType,reportedZipCode"
)
CLAIM_FIELDS = (
    "yearOfLoss,amountPaidOnBuildingClaim,amountPaidOnContentsClaim,"
    "amountPaidOnIncreasedCostOfComplianceClaim,ratedFloodZone,causeOfDamage"
)
HIGH = "High risk (A and V zones)"
LOW = "Moderate or low risk (B, C, X)"
# OpenFEMA v3 codes single-family as 11 (legacy 1).
SINGLE_FAMILY_CODES = ("1", "11")
SOURCE_NOTE = "aggregates only; FEMA redacted dataset, no policyholder identity"


def fetch_all(url: str, entity: str, select: str) -> tuple[list, str | None]:
    """Page through an OpenFEMA entity; returns (rows, metadata asOfDate or None)."""
    rows: list = []
    as_of = None
    skip = 0
    while True:
        params = {
            "$filter": COMMUNITY_FILTER, "$select": select, "$top": PAGE,
            "$skip": skip, "$inlinecount": "allpages",
        }
        doc = get_json(url, params=params)
        meta = doc.get("metadata") or {}
        as_of = as_of or meta.get("asOfDate")
        batch = doc.get(entity) or []
        rows.extend(batch)
        total = int(meta.get("count") or 0)
        skip += PAGE
        if not batch or skip >= total:
            break
    return rows, as_of


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


def _day(v) -> str:
    return str(v or "")[:10]


def zone_group(zone) -> str:
    z = str(zone or "").strip().upper()
    return HIGH if z[:1] in ("A", "V") else LOW


def decade_label(year: int) -> str:
    return f"{year // 10 * 10}s"


def in_force(row: dict, today: str) -> bool:
    eff, term = _day(row.get("policyEffectiveDate")), _day(row.get("policyTerminationDate"))
    return bool(eff) and bool(term) and eff <= today < term


def aggregate_policies(rows: list, today: str) -> dict:
    live = [r for r in rows if in_force(r, today)]
    count = sum(int(_num(r.get("policyCount")) or 1) for r in live)
    premiums = [_num(r.get("totalInsurancePremiumOfThePolicy")) / (int(_num(r.get("policyCount")) or 1))
                for r in live]
    by_zone = {HIGH: 0, LOW: 0}
    by_occ = {"Single family": 0, "Other": 0}
    for r in live:
        n = int(_num(r.get("policyCount")) or 1)
        by_zone[zone_group(r.get("ratedFloodZone"))] += n
        by_occ["Single family" if str(r.get("occupancyType")) in SINGLE_FAMILY_CODES else "Other"] += n
    return {
        "policies_in_force": {
            "count": count,
            "building_coverage": round(sum(_num(r.get("totalBuildingInsuranceCoverage")) for r in live)),
            "contents_coverage": round(sum(_num(r.get("totalContentsInsuranceCoverage")) for r in live)),
            "annual_premium": round(sum(_num(r.get("totalInsurancePremiumOfThePolicy")) for r in live)),
            "median_premium": round(statistics.median(premiums)) if premiums else 0,
        },
        "policies_in_force_by_zone": [{"zone_group": k, "count": v} for k, v in by_zone.items()],
        "policies_by_occupancy": [{"occupancy": k, "count": v} for k, v in by_occ.items()],
    }


def claim_paid(r: dict) -> float:
    return (_num(r.get("amountPaidOnBuildingClaim")) + _num(r.get("amountPaidOnContentsClaim"))
            + _num(r.get("amountPaidOnIncreasedCostOfComplianceClaim")))


def aggregate_claims(rows: list) -> dict:
    usable = [r for r in rows if isinstance(r.get("yearOfLoss"), int)]
    decades: dict[str, dict] = {}
    years: dict[int, float] = {}
    for r in usable:
        d = decades.setdefault(decade_label(r["yearOfLoss"]), {"count": 0, "paid": 0.0})
        d["count"] += 1
        d["paid"] += claim_paid(r)
        years[r["yearOfLoss"]] = years.get(r["yearOfLoss"], 0.0) + claim_paid(r)
    by_decade = [{"decade": k, "count": v["count"], "paid": round(v["paid"])} for k, v in sorted(decades.items())]
    top = max(years.items(), key=lambda kv: kv[1]) if years else (0, 0.0)
    return {
        "claims_total": {"count": len(usable), "paid": round(sum(claim_paid(r) for r in usable))},
        "claims_by_decade": by_decade,
        "largest_claim_year": {"year": top[0], "paid": round(top[1])},
    }


def check_plausible(out: dict) -> list[str]:
    problems = []
    n = out["policies_in_force"]["count"]
    if not 5 <= n <= 500:
        problems.append(f"policies_in_force {n} outside 5-500")
    c = out["claims_total"]["count"]
    if not 10 <= c <= 500:
        problems.append(f"claims_total {c} outside 10-500")
    if len(out["claims_by_decade"]) < 3:
        problems.append(f"only {len(out['claims_by_decade'])} claim decades (need at least 3)")
    return problems


def build(policies: list, claims: list, as_of: str | None, today: str) -> dict:
    out = aggregate_policies(policies, today)
    out.update(aggregate_claims(claims))
    out["as_of"] = (as_of or today)[:10]
    out["extracted"] = today
    out["_source"] = {
        "policies": POLICIES_URL, "claims": CLAIMS_URL, "note": SOURCE_NOTE,
    }
    return out


def main() -> int:
    today = dt.date.today().isoformat()
    print("Fetching OpenFEMA NFIP v3 (Burton, City of):")
    policies, as_of_p = fetch_all(POLICIES_URL, "NfipPolicies", POLICY_FIELDS)
    claims, as_of_c = fetch_all(CLAIMS_URL, "NfipClaims", CLAIM_FIELDS)
    print(f"  policy term rows: {len(policies)}  claim rows: {len(claims)}")
    out = build(policies, claims, as_of_p or as_of_c, today)
    problems = check_plausible(out)
    if problems:
        print("REFUSING to write: " + "; ".join(problems))
        return 1
    write_json(OUT, out)
    p, c = out["policies_in_force"], out["claims_total"]
    print(f"  in force: {p['count']} (median premium ${p['median_premium']})  by zone: {out['policies_in_force_by_zone']}")
    print(f"  claims: {c['count']} paid ${c['paid']:,}  decades: {len(out['claims_by_decade'])}  largest year: {out['largest_claim_year']}")
    print(f"  as_of: {out['as_of']}  guards: policies 5-500 ok, claims 10-500 ok, decades>=3 ok")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
