"""Unit tests for the NFIP aggregator and its merge into the Environment panel (no network)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fetch_environment as fe  # noqa: E402
import fetch_flood_insurance as ff  # noqa: E402

TODAY = "2026-10-07"


def pol(eff, term, zone="X", occ=1, prem=800.0, n=1):
    return {"policyCount": n, "totalBuildingInsuranceCoverage": 100000, "totalContentsInsuranceCoverage": 20000,
            "totalInsurancePremiumOfThePolicy": prem, "policyEffectiveDate": eff + "T00:00:00.000Z",
            "policyTerminationDate": term + "T00:00:00.000Z", "ratedFloodZone": zone, "occupancyType": occ}


def test_in_force_filter_by_dates():
    assert ff.in_force(pol("2026-01-01", "2027-01-01"), TODAY)
    assert ff.in_force(pol("2026-10-07", "2027-10-07"), TODAY)       # effective today counts
    assert not ff.in_force(pol("2025-01-01", "2026-10-07"), TODAY)   # terminates today: out
    assert not ff.in_force(pol("2026-10-08", "2027-10-08"), TODAY)   # not yet effective
    assert not ff.in_force({"policyEffectiveDate": None, "policyTerminationDate": None}, TODAY)


def test_zone_grouping():
    assert ff.zone_group("AE") == ff.HIGH
    assert ff.zone_group("A05") == ff.HIGH
    assert ff.zone_group("VE") == ff.HIGH
    assert ff.zone_group("X") == ff.LOW
    assert ff.zone_group("B") == ff.LOW
    assert ff.zone_group(None) == ff.LOW


def test_aggregate_policies_counts_only_in_force():
    rows = [pol("2026-01-01", "2027-01-01", "AE", 11, 1000), pol("2026-02-01", "2027-02-01", "X", 4, 500, n=2),
            pol("2020-01-01", "2021-01-01", "AE")]
    a = ff.aggregate_policies(rows, TODAY)
    assert a["policies_in_force"]["count"] == 3
    assert a["policies_in_force"]["annual_premium"] == 1500
    assert {z["zone_group"]: z["count"] for z in a["policies_in_force_by_zone"]} == {ff.HIGH: 1, ff.LOW: 2}
    assert {o["occupancy"]: o["count"] for o in a["policies_by_occupancy"]} == {"Single family": 1, "Other": 2}


def test_decade_grouping_and_paid_total():
    claims = [{"yearOfLoss": 1987, "amountPaidOnBuildingClaim": 100.0, "amountPaidOnContentsClaim": 50.0},
              {"yearOfLoss": 1989, "amountPaidOnBuildingClaim": None},
              {"yearOfLoss": 2019, "amountPaidOnBuildingClaim": 1000.0, "amountPaidOnIncreasedCostOfComplianceClaim": 500.0},
              {"yearOfLoss": None}]
    a = ff.aggregate_claims(claims)
    assert a["claims_by_decade"] == [{"decade": "1980s", "count": 2, "paid": 150}, {"decade": "2010s", "count": 1, "paid": 1500}]
    assert a["claims_total"] == {"count": 3, "paid": 1650}
    assert a["largest_claim_year"] == {"year": 2019, "paid": 1500}


def _good():
    policies = [pol("2026-01-01", "2027-01-01", "AE") for _ in range(6)]
    claims = [{"yearOfLoss": 1980 + i * 10, "amountPaidOnBuildingClaim": 10.0} for i in range(4)] * 3
    return ff.build(policies, claims, None, TODAY)


def test_plausibility_guard():
    assert ff.check_plausible(_good()) == []
    bad = _good()
    bad["policies_in_force"]["count"] = 2
    bad["claims_total"]["count"] = 3
    bad["claims_by_decade"] = bad["claims_by_decade"][:2]
    assert len(ff.check_plausible(bad)) == 3


def test_fetch_all_pages_and_main_refuses_implausible(monkeypatch, tmp_path):
    calls = []

    def fake(url, params=None, **kw):
        calls.append(params["$skip"])
        return {"metadata": {"count": 1500, "asOfDate": "2026-09-30T00:00:00Z"},
                "NfipPolicies": [{"policyCount": 1}] * (1000 if params["$skip"] == 0 else 500)}

    monkeypatch.setattr(ff, "get_json", fake)
    rows, as_of = ff.fetch_all(ff.POLICIES_URL, "NfipPolicies", ff.POLICY_FIELDS)
    assert len(rows) == 1500 and calls == [0, 1000] and as_of.startswith("2026-09-30")
    # main(): no in-force policies -> refuses to write
    monkeypatch.setattr(ff, "OUT", str(tmp_path / "out.json"))
    assert ff.main() == 1
    assert not (tmp_path / "out.json").exists()


def test_panel_merge_and_boundary_validation(tmp_path):
    out = _good()
    panel = {"stats": [{"label": "a", "value": "1"}], "charts": [], "notes": [], "links": [], "source": "EPA."}
    path = tmp_path / "nfip.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    nfip = fe.load_nfip(str(path))
    fe.add_flood(panel, nfip)
    labels = [s["label"] for s in panel["stats"]]
    assert labels[1:] == ["Flood insurance policies in force", "Homes in high-risk zones with a policy",
                          "Flood claims paid since 1978", "Typical annual premium"]
    assert [c["type"] for c in panel["charts"]] == ["bars", "donut"]
    assert panel["links"][-1]["href"] == "https://msc.fema.gov/portal/home"
    assert "OpenFEMA" in panel["source"]
    assert fe.load_nfip(str(tmp_path / "missing.json")) is None
    out["claims_by_decade"] = []
    path.write_text(json.dumps(out), encoding="utf-8")
    with pytest.raises(SystemExit):
        fe.load_nfip(str(path))
