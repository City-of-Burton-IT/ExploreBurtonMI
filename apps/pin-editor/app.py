# Pin editor -- local Flask app (http://pins.local). Single user, 127.0.0.1 only.
# Edits the Explore Burton business list on a Leaflet map and writes the pipeline's
# SOURCE files, regenerates data.geojson, then commits + pushes on Publish.
#
# Run:  run.cmd   (or:  .venv\Scripts\python.exe app.py)
from __future__ import annotations

import hmac
import os
import secrets

from flask import Flask, abort, jsonify, render_template, request, send_file, session

import excel
import store
from edits import apply_edits

app = Flask(__name__)
# Ephemeral key: sessions reset on restart, which is fine for a local single-user tool.
app.secret_key = secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_last = {"regenerate": None, "publish": None}


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


@app.before_request
def _csrf_guard():
    # Mutating API calls have real side effects (file writes, git push); require the token.
    if request.method in _MUTATING and request.path.startswith("/api/"):
        sent = request.headers.get("X-CSRF-Token", "")
        have = session.get("csrf_token", "")
        if not have or not sent or not hmac.compare_digest(have, sent):
            abort(403)


@app.route("/")
def index():
    return render_template("index.html", csrf_token=_csrf_token())


@app.get("/api/data")
def api_data():
    data = store.load_data()
    return jsonify({
        "features": data.get("features", []),
        "categories": store.CATEGORIES,
        "bbox": store.CITY_BBOX,
    })


@app.post("/api/save")
def api_save():
    edits = (request.get_json(silent=True) or {}).get("edits", [])
    if not isinstance(edits, list):
        return jsonify({"ok": False, "error": "edits must be a list"}), 400
    facilities, overrides = store.load_facilities(), store.load_overrides()
    facilities, overrides = apply_edits(facilities, overrides, edits)
    store.save_sources(facilities, overrides)
    return jsonify({"ok": True, "applied": len(edits)})


@app.post("/api/regenerate")
def api_regenerate():
    result = store.run_pipeline()
    _last["regenerate"] = result
    return jsonify(result)


@app.get("/api/export.xlsx")
def api_export():
    rows = excel.features_to_rows(store.load_data().get("features", []))
    bio = store.build_pins_workbook(rows)
    return send_file(
        bio, as_attachment=True, download_name="burton-pins.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/api/import")
def api_import():
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "No file uploaded."}), 400
    try:
        rows = store.read_pins_rows(f)
    except Exception as e:  # malformed / non-xlsx upload
        app.logger.warning("Workbook import rejected: %s", e)
        return jsonify({"ok": False, "error": "Could not read that workbook."}), 400
    feats = store.load_data().get("features", [])
    edits, warnings = excel.rows_to_edits(rows, feats, store.CATEGORIES, store.CITY_BBOX)
    return jsonify({"ok": True, "edits": edits, "warnings": warnings})


@app.get("/api/boundary")
def api_boundary():
    try:
        return jsonify(store.load_boundary())
    except FileNotFoundError:
        return jsonify({}), 404


@app.get("/api/diff")
def api_diff():
    return jsonify({"diff": store.git_diff_stat()})


@app.post("/api/publish")
def api_publish():
    summary = (request.get_json(silent=True) or {}).get("summary", "")
    summary = " ".join(str(summary).split())[:120]  # one line, bounded
    message = "data: pin editor" + (f" ({summary})" if summary else "")
    result = store.git_publish(message)
    _last["publish"] = result
    return jsonify(result)


@app.get("/api/status")
def api_status():
    return jsonify(_last)


@app.errorhandler(500)
def _server_error(e):
    app.logger.error("Unhandled error: %s", e, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(413)
def _workbook_too_large(_e):
    return jsonify({"ok": False, "error": "Workbook is too large."}), 413


def main() -> None:
    from waitress import serve
    host = "127.0.0.1"
    port = int(os.environ.get("PIN_EDITOR_PORT", "80"))
    print(f"Pin editor running -> http://pins.local  (bound {host}:{port})")
    print("Ctrl+C to stop.")
    serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
