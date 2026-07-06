# Unit tests for the shared tools/lib helpers. No network.
# Run: python -m pytest tools/test_lib.py -q
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from lib import arcgis, geo, httpio, iox, paths, shapecheck  # noqa: E402


# --- geo.round_coords ---------------------------------------------------------

def test_round_coords_point_pair():
    assert geo.round_coords([1.234567, -83.9876543]) == [1.23457, -83.98765]


def test_round_coords_nested_polygon():
    poly = [[[1.111111, 2.222222], [3.333333, 4.444444]]]
    assert geo.round_coords(poly) == [[[1.11111, 2.22222], [3.33333, 4.44444]]]


def test_round_coords_custom_digits():
    assert geo.round_coords([1.2345, 2.3456], ndigits=2) == [1.23, 2.35]


# --- paths ---------------------------------------------------------------------

def test_repo_root_is_the_repo():
    assert os.path.isfile(os.path.join(paths.REPO_ROOT, "package.json"))


def test_public_and_pipeline_paths():
    assert paths.public_path("boundary.geojson").endswith(
        os.path.join("public", "boundary.geojson")
    )
    assert paths.pipeline_data_path("x.json").endswith(
        os.path.join("pipeline", "data", "x.json")
    )


# --- iox -------------------------------------------------------------------------

def test_write_geojson_is_compact_with_trailing_newline(tmp_path):
    p = str(tmp_path / "out.geojson")
    iox.write_geojson(p, {"type": "FeatureCollection", "features": []})
    raw = open(p, encoding="utf-8", newline="").read()
    assert raw == '{"type":"FeatureCollection","features":[]}\n'


def test_write_json_is_indented_with_trailing_newline(tmp_path):
    p = str(tmp_path / "panel.json")
    iox.write_json(p, {"a": 1})
    raw = open(p, encoding="utf-8", newline="").read()
    assert raw == '{\n  "a": 1\n}\n'
    assert json.load(open(p, encoding="utf-8")) == {"a": 1}


def test_write_replaces_atomically(tmp_path):
    p = str(tmp_path / "out.json")
    iox.write_json(p, {"v": 1})
    iox.write_json(p, {"v": 2})
    assert json.load(open(p, encoding="utf-8")) == {"v": 2}
    assert not os.path.exists(p + ".tmp")


# --- shapecheck ------------------------------------------------------------------

def test_assert_shape_passes_and_returns_rows():
    rows = [{"a": 1, "b": 2}]
    assert shapecheck.assert_shape(rows, ["a", "b"]) is rows


def test_assert_shape_fails_on_missing_key():
    with pytest.raises(SystemExit, match="missing required keys"):
        shapecheck.assert_shape([{"a": 1}], ["a", "b"], "test rows")


def test_assert_shape_fails_on_empty():
    with pytest.raises(SystemExit, match="no rows"):
        shapecheck.assert_shape([], ["a"])


# --- httpio ------------------------------------------------------------------------

class _FakeResp:
    """Minimal stand-in for the context-manager object urllib.request.urlopen
    returns; json.load only needs .read()."""

    def __init__(self, payload):
        self._payload = payload

    def read(self, *a):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_get_json_retries_then_succeeds(monkeypatch):
    calls, sleeps = [], []

    def fake_urlopen(req, timeout=None):
        calls.append(timeout)
        if len(calls) < 3:
            raise OSError("transient")
        return _FakeResp({"ok": True})

    monkeypatch.setattr(httpio.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(httpio.time, "sleep", lambda s: sleeps.append(s))
    assert httpio.get_json("http://example.test/x", timeout=30) == {"ok": True}
    assert calls == [30, 50, 70]  # escalating read timeout, +20 s per retry
    assert len(sleeps) == 2


def test_get_json_exhausts_attempts_and_raises(monkeypatch):
    monkeypatch.setattr(httpio.urllib.request, "urlopen",
                        lambda req, timeout=None: (_ for _ in ()).throw(OSError("down")))
    monkeypatch.setattr(httpio.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="all 2 attempts failed"):
        httpio.get_json("http://example.test/x", attempts=2)


def test_get_json_encodes_params(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(req.full_url)
        return _FakeResp([])

    monkeypatch.setattr(httpio.urllib.request, "urlopen", fake_urlopen)
    httpio.get_json("http://example.test/q", params={"a": "1", "b": "x y"})
    assert seen == ["http://example.test/q?a=1&b=x+y"]


def test_post_json_sends_payload_and_retries(monkeypatch):
    calls, sleeps = [], []

    def fake_urlopen(req, timeout=None):
        calls.append((req.data, req.get_header("Content-type")))
        if len(calls) < 2:
            raise OSError("transient")
        return _FakeResp({"ok": 1})

    monkeypatch.setattr(httpio.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(httpio.time, "sleep", lambda s: sleeps.append(s))
    assert httpio.post_json("http://example.test/p", {"q": 2}) == {"ok": 1}
    assert calls[0] == (b'{"q": 2}', "application/json")
    assert len(calls) == 2 and len(sleeps) == 1


# --- arcgis.paged_query ------------------------------------------------------------

def test_paged_query_pages_until_short_page(monkeypatch):
    calls = []

    def fake_get_json(url, params=None, attempts=4, timeout=60):
        calls.append(dict(params))
        offset = int(params["resultOffset"])
        # two full pages of 2, then a short page of 1
        n = 2 if offset < 4 else 1
        return {"features": [{"id": offset + i} for i in range(n)]}

    monkeypatch.setattr(arcgis, "get_json", fake_get_json)
    feats = list(arcgis.paged_query("http://x/query", {"f": "geojson"}, page_size=2))
    assert [f["id"] for f in feats] == [0, 1, 2, 3, 4]
    assert [c["resultOffset"] for c in calls] == ["0", "2", "4"]
    # base params are passed through untouched on every page
    assert all(c["f"] == "geojson" for c in calls)


def test_paged_query_single_short_page(monkeypatch):
    monkeypatch.setattr(arcgis, "get_json", lambda *a, **k: {"features": [{"id": 1}]})
    assert len(list(arcgis.paged_query("http://x", {}, page_size=1000))) == 1
