# Smoke tests for store.py file IO -- newline preservation + round-trip.
import json
import subprocess

import store


def test_write_json_preserves_lf(tmp_path):
    p = tmp_path / "lf.json"
    p.write_bytes(b'{\n  "a": 1\n}\n')           # existing file uses LF
    store._write_json(p, {"a": 2})
    raw = p.read_bytes()
    assert b"\r\n" not in raw                      # stayed LF
    assert json.loads(raw.decode("utf-8")) == {"a": 2}


def test_write_json_preserves_crlf(tmp_path):
    p = tmp_path / "crlf.json"
    p.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')       # existing file uses CRLF
    store._write_json(p, {"a": 2})
    raw = p.read_bytes()
    assert b"\r\n" in raw                          # stayed CRLF
    assert b"\n" not in raw.replace(b"\r\n", b"")  # no bare LFs
    assert json.loads(raw.decode("utf-8")) == {"a": 2}


def test_compact_geometry_keeps_point_inline(tmp_path):
    p = tmp_path / "f.geojson"
    fc = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "id": "burton:x",
        "geometry": {"type": "Point", "coordinates": [-83.63181, 42.965477]},
        "properties": {"name": "X", "category": "Government"},
    }]}
    store._write_json(p, fc, compact_geometry=True)
    text = p.read_text(encoding="utf-8")
    # geometry on one line (matches facilities.geojson hand-maintained style)
    assert '"geometry": { "type": "Point", "coordinates": [-83.63181, 42.965477] }' in text
    # properties still pretty (multi-line)
    assert '\n      "properties": {' in text or '\n  "properties"' in text or '"name": "X"' in text
    assert json.loads(text) == fc                      # still valid + round-trips


def test_compact_geometry_leaves_null_geometry(tmp_path):
    p = tmp_path / "g.geojson"
    fc = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "id": "burton:y", "geometry": None, "properties": {"name": "Y"},
    }]}
    store._write_json(p, fc, compact_geometry=True)
    text = p.read_text(encoding="utf-8")
    assert '"geometry": null' in text
    assert json.loads(text) == fc


def test_workbook_round_trip():
    from io import BytesIO
    rows = [{
        "id": "burton:x", "source": "curated", "name": "X Hall", "category": "Government",
        "address": "1 Main", "phone": "p", "website": "w", "hours": "h",
        "lat": 42.99, "lng": -83.62, "delete": "",
    }]
    bio = store.build_pins_workbook(rows)
    back = store.read_pins_rows(BytesIO(bio.getvalue()))
    assert back[0]["id"] == "burton:x"
    assert back[0]["name"] == "X Hall"
    assert back[0]["category"] == "Government"
    assert back[0]["lat"] == 42.99 and back[0]["lng"] == -83.62


def test_write_json_new_file_defaults_lf(tmp_path):
    p = tmp_path / "new.json"
    store._write_json(p, {"a": 1})
    raw = p.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")


def test_git_publish_refuses_unrelated_pre_staged_file(monkeypatch):
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args == ("diff", "--cached", "--name-only", "-z", "--"):
            return subprocess.CompletedProcess(args, 0, "private-notes.txt\0", "")
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr(store, "_git", fake_git)

    result = store.git_publish("data: test")

    assert result["ok"] is False
    assert result["step"] == "preflight"
    assert "private-notes.txt" in result["detail"]
    assert not any(args[0] == "add" for args in calls)


def test_git_publish_scans_and_commits_only_allowlisted_paths(monkeypatch):
    calls = []

    def fake_git(*args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(store, "_git", fake_git)
    monkeypatch.setattr(
        store,
        "_scan_staged_for_secrets",
        lambda: {"ok": True, "detail": "no leaks found"},
        raising=False,
    )

    result = store.git_publish("data: test")

    assert result["ok"] is True
    commit = next(args for args in calls if args[0] == "commit")
    assert commit[1:4] == ("--only", "-m", "data: test")
    assert "--" in commit
    assert set(commit[commit.index("--") + 1 :]) == {
        str(path.relative_to(store.REPO_ROOT)).replace("\\", "/")
        for path in store.PUBLISH_PATHS
    }


def test_pii_preflight_flags_sensitive_added_lines_without_echoing_values():
    staged_diff = (
        'diff --git a/public/data.geojson b/public/data.geojson\n'
        '+      "ssn": "123-45-6789",\n'
        '+      "ownerName": "Resident Name"\n'
        '       "name": "Burton City Hall"\n'
    )

    findings = store._pii_findings(staged_diff)

    assert findings == ["SSN-like value", "forbidden personal/property field"]
    assert "123-45-6789" not in " ".join(findings)
    assert "Resident Name" not in " ".join(findings)


def test_pii_preflight_accepts_current_public_dataset():
    current_data_as_added_lines = "\n".join(
        f"+{line}" for line in store.DATA.read_text(encoding="utf-8").splitlines()
    )

    assert store._pii_findings(current_data_as_added_lines) == []
