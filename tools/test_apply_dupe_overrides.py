# Tests for apply_dupe_overrides.py: it writes pipeline/data/overrides.json,
# which pipeline/run.py merges verbatim into production data, so its merge
# logic is tested here against temp files (tmp_path) -- the real overrides.json
# and the real public/data.geojson are never touched.
# Run: python -m pytest tools/test_apply_dupe_overrides.py -q
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import apply_dupe_overrides as ado  # noqa: E402
import find_dupes as fd  # noqa: E402


def _feature(id_, name, address, phone=None, category=None):
    props = {"name": name, "address": address}
    if phone is not None:
        props["phone"] = phone
    if category is not None:
        props["category"] = category
    return {"id": id_, "properties": props}


def _write_data(tmp_path, features):
    path = tmp_path / "data.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return str(path)


# --- build_decisions --------------------------------------------------------------

def test_build_decisions_hides_the_less_complete_variant(tmp_path, monkeypatch):
    features = [
        _feature("survivor-1", "Chase Bank", "100 Main St", phone="555-1000"),
        _feature("dupe-1", "Chase", "100 Main St"),
    ]
    monkeypatch.setattr(fd, "DATA", _write_data(tmp_path, features))
    monkeypatch.setattr(ado, "PROTECT", set())

    hides, protected = ado.build_decisions()

    assert protected == []
    assert len(hides) == 1
    hidden, survivor = hides[0]
    assert hidden["id"] == "dupe-1"
    assert survivor["id"] == "survivor-1"


def test_build_decisions_ignores_unrelated_addresses_and_singletons(tmp_path, monkeypatch):
    features = [
        _feature("a", "Chase Bank", "100 Main St"),
        _feature("b", "Speedway", "200 Oak Ave"),  # different address, no cluster
    ]
    monkeypatch.setattr(fd, "DATA", _write_data(tmp_path, features))
    monkeypatch.setattr(ado, "PROTECT", set())

    hides, protected = ado.build_decisions()
    assert hides == []
    assert protected == []


def test_build_decisions_respects_protect_set(tmp_path, monkeypatch):
    # Mirrors the real PROTECT case: a co-located, genuinely distinct POI whose
    # name happens to CONTAIN the survivor's name (e.g. "Dog Park at Our Risen
    # Lord Lutheran Church" vs. "Our Risen Lord Lutheran Church"), so the
    # name-overlap heuristic clusters them as variants even though they aren't.
    features = [
        _feature("survivor-1", "Our Risen Lord Lutheran Church", "1 Faith Way", phone="555-2000"),
        _feature("protected-1", "Dog Park at Our Risen Lord Lutheran Church", "1 Faith Way"),
    ]
    monkeypatch.setattr(fd, "DATA", _write_data(tmp_path, features))
    monkeypatch.setattr(ado, "PROTECT", {"protected-1"})

    hides, protected = ado.build_decisions()
    assert hides == []
    assert [p["id"] for p in protected] == ["protected-1"]


# --- main(): dry run vs --write, and the merge rules ------------------------------

def _setup(tmp_path, monkeypatch, features, existing_overrides, bigbox=None):
    monkeypatch.setattr(fd, "DATA", _write_data(tmp_path, features))
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps(existing_overrides), encoding="utf-8")
    monkeypatch.setattr(ado, "OVERRIDES", str(overrides_path))
    monkeypatch.setattr(ado, "PROTECT", set())
    monkeypatch.setattr(ado, "BIGBOX_ENRICH", bigbox or {})
    return overrides_path


def test_main_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    features = [
        _feature("survivor-1", "Chase Bank", "100 Main St", phone="555-1000"),
        _feature("dupe-1", "Chase", "100 Main St"),
    ]
    overrides_path = _setup(tmp_path, monkeypatch, features, {})
    before = overrides_path.read_text()

    monkeypatch.setattr(sys, "argv", ["apply_dupe_overrides.py"])
    rc = ado.main()

    assert rc == 0
    assert overrides_path.read_text() == before  # untouched
    out = capsys.readouterr().out
    assert "dry run" in out


def test_main_write_adds_new_hide_entry(tmp_path, monkeypatch):
    features = [
        _feature("survivor-1", "Chase Bank", "100 Main St", phone="555-1000"),
        _feature("dupe-1", "Chase", "100 Main St"),
    ]
    overrides_path = _setup(tmp_path, monkeypatch, features, {})

    monkeypatch.setattr(sys, "argv", ["apply_dupe_overrides.py", "--write"])
    rc = ado.main()

    assert rc == 0
    written = json.loads(overrides_path.read_text())
    assert written["dupe-1"]["hidden"] is True
    assert "survivor-1" in written["dupe-1"]["_why"]


def test_main_folds_hidden_into_existing_enrichment(tmp_path, monkeypatch):
    # A record that already carries a manual enrichment override (e.g. phone) but
    # is now a confirmed duplicate: hidden:true should fold in without dropping
    # the pre-existing enrichment fields.
    features = [
        _feature("survivor-1", "Chase Bank", "100 Main St", phone="555-1000"),
        _feature("dupe-1", "Chase", "100 Main St"),
    ]
    existing = {"dupe-1": {"website": "https://example.com/chase"}}
    overrides_path = _setup(tmp_path, monkeypatch, features, existing)

    monkeypatch.setattr(sys, "argv", ["apply_dupe_overrides.py", "--write"])
    ado.main()

    written = json.loads(overrides_path.read_text())
    assert written["dupe-1"]["hidden"] is True
    assert written["dupe-1"]["website"] == "https://example.com/chase"  # preserved


def test_main_leaves_already_hidden_records_alone(tmp_path, monkeypatch):
    features = [
        _feature("survivor-1", "Chase Bank", "100 Main St", phone="555-1000"),
        _feature("dupe-1", "Chase", "100 Main St"),
    ]
    existing = {"dupe-1": {"hidden": True, "_why": "manually hidden earlier"}}
    overrides_path = _setup(tmp_path, monkeypatch, features, existing)

    monkeypatch.setattr(sys, "argv", ["apply_dupe_overrides.py", "--write"])
    ado.main()

    written = json.loads(overrides_path.read_text())
    assert written["dupe-1"] == {"hidden": True, "_why": "manually hidden earlier"}


def test_main_merges_bigbox_enrich_entries(tmp_path, monkeypatch):
    overrides_path = _setup(
        tmp_path, monkeypatch, features=[],
        existing_overrides={},
        bigbox={"survivor-x": {"services": ["Pharmacy"], "_why": "big-box collapse"}},
    )
    monkeypatch.setattr(sys, "argv", ["apply_dupe_overrides.py", "--write"])
    ado.main()

    written = json.loads(overrides_path.read_text())
    assert written["survivor-x"]["services"] == ["Pharmacy"]
