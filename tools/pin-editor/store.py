# Pin-editor IO + pipeline + git layer. Resolves repo paths, loads/saves the source
# and generated GeoJSON (preserving each file's existing line endings so git diffs stay
# minimal), runs the data pipeline, and does the git publish. Kept separate from the
# pure routing in edits.py so the routing stays trivially testable.
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# tools/pin-editor/store.py -> repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
FACILITIES = REPO_ROOT / "pipeline" / "data" / "facilities.geojson"
OVERRIDES = REPO_ROOT / "pipeline" / "data" / "overrides.json"
DATA = REPO_ROOT / "public" / "data.geojson"
BOUNDARY = REPO_ROOT / "public" / "boundary.geojson"
PIPELINE_DIR = REPO_ROOT / "pipeline"
_PIPELINE_PY = PIPELINE_DIR / ".venv" / "Scripts" / "python.exe"

# Files the publish step stages (source + everything the pipeline regenerates).
PUBLISH_PATHS = [FACILITIES, OVERRIDES, DATA, BOUNDARY]

# City bounding box (min_lng, min_lat, max_lng, max_lat) -- mirrors the pipeline's
# validation extent; used to warn on out-of-city adds/moves.
CITY_BBOX = (-83.85, 42.85, -83.40, 43.15)

# Controlled category vocabulary (the distinct categories the public map uses).
CATEGORIES = [
    "Government", "Public Safety", "Public Works", "Parks & Recreation",
    "Community Services", "Education", "Faith", "Health & Medical",
    "Dining", "Grocery & Food", "Retail & Shopping", "Automotive",
    "Professional & Personal Services", "Financial", "Arts & Entertainment",
    "Lodging",
]


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compact_geometry(text: str) -> str:
    """Collapse each pretty-printed `"geometry": { ... }` block onto one line to match
    facilities.geojson's hand-maintained style -- so unchanged features produce no diff.
    A Point geometry has no nested braces, so `\\{[^}]*\\}` matches it cleanly."""
    def repl(m: "re.Match") -> str:
        obj = json.loads(m.group(1))
        compact = json.dumps(obj, separators=(", ", ": "))
        return '"geometry": { ' + compact[1:-1] + " }"
    return re.sub(r'"geometry":\s*(\{[^}]*\})', repl, text)


def _write_json(path: Path, obj: dict, compact_geometry: bool = False) -> None:
    """Write pretty JSON, preserving the file's existing newline style (LF vs CRLF).
    With compact_geometry, geometry objects are kept inline (facilities.geojson style)."""
    raw = path.read_bytes() if path.exists() else b""
    eol = "\r\n" if b"\r\n" in raw else "\n"
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if compact_geometry:
        text = _compact_geometry(text)
    if not text.endswith("\n"):
        text += "\n"
    if eol == "\r\n":
        text = text.replace("\n", "\r\n")
    # newline="" so Python does not translate the line endings we just set.
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def load_facilities() -> dict:
    return _read_json(FACILITIES)


def load_overrides() -> dict:
    return _read_json(OVERRIDES)


def load_data() -> dict:
    return _read_json(DATA)


def load_boundary() -> dict:
    return _read_json(BOUNDARY)


def save_sources(facilities: dict, overrides: dict) -> None:
    _write_json(FACILITIES, facilities, compact_geometry=True)
    _write_json(OVERRIDES, overrides)


def _pipeline_python() -> str:
    return str(_PIPELINE_PY) if _PIPELINE_PY.exists() else sys.executable


def run_pipeline() -> dict:
    """Run pipeline/run.py (cached sources, no network). Returns ok/stdout/stderr/counts."""
    before = len(load_data().get("features", [])) if DATA.exists() else 0
    proc = subprocess.run(
        [_pipeline_python(), "run.py"],
        cwd=str(PIPELINE_DIR), capture_output=True, text=True,
    )
    after = len(load_data().get("features", [])) if DATA.exists() else 0
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "before": before,
        "after": after,
    }


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True,
    )


def git_diff_stat() -> str:
    rels = [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in PUBLISH_PATHS]
    proc = _git("diff", "--stat", "--", *rels)
    return proc.stdout.strip() or "(no changes)"


def git_publish(message: str) -> dict:
    """Stage the data files, commit, and push the current branch. Never force-pushes."""
    rels = [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in PUBLISH_PATHS]
    add = _git("add", "--", *rels)
    if add.returncode != 0:
        return {"ok": False, "step": "add", "detail": add.stderr.strip()}
    commit = _git("commit", "-m", message)
    if commit.returncode != 0:
        out = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in out:
            return {"ok": False, "step": "commit", "detail": "Nothing to commit (no staged changes)."}
        return {"ok": False, "step": "commit", "detail": (commit.stdout + commit.stderr).strip()}
    push = _git("push")
    if push.returncode != 0:
        return {"ok": False, "step": "push", "detail": (push.stdout + push.stderr).strip(),
                "committed": True}
    return {"ok": True, "detail": (commit.stdout + push.stderr).strip()}
