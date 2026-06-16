# Smoke tests for store.py file IO -- newline preservation + round-trip.
import json

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


def test_write_json_new_file_defaults_lf(tmp_path):
    p = tmp_path / "new.json"
    store._write_json(p, {"a": 1})
    raw = p.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
