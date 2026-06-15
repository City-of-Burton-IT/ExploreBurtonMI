"""Apply approved listing change requests (#3) to the committed data files.

Reads rows with Status=Approved from the "Explore Burton Listing Requests"
SharePoint list (the moderation queue behind the in-app "Suggest an edit"
form), converts each into the existing correction mechanism, and marks the
row Applied:

  Fix listing / Moved   -> an entry in pipeline/data/overrides.json
  Permanently closed    -> {"hidden": true} override
  Add my business       -> a CANDIDATE feature written to
                           tools/pending-additions.json for manual vetting
                           (dedup vs OSM/Overture, category, in-city check)
                           before pasting into pipeline/data/facilities.geojson.

PRIVACY: submitter contact details are deliberately NEVER copied into the
committed files -- the _why notes reference the queue row number only.

After a run: re-run the pipeline (python pipeline/run.py), review the git
diff, commit, push. Nothing is published by this tool directly.

Usage:
    python tools/sync_listing_requests.py            # apply + mark rows Applied
    python tools/sync_listing_requests.py --dry-run  # show what would happen

Auth: delegated Graph token via the local outlook-mcp token store (refresh
grant; the same client the MCP uses). Paths/names can be overridden with
EXPLORE_TOKEN_STORE / EXPLORE_MCP_ENV env vars. No secrets in this file.
Designed so the pure transforms can be reused by a future approval-triggered
GitHub Action that receives row fields in a repository_dispatch payload.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date

SITE = os.environ.get("EXPLORE_SP_SITE", "burtonmi.sharepoint.com:/sites/ITDepartment")
LIST_ID = os.environ.get("EXPLORE_SP_LIST", "f5b45cd8-c582-414b-b330-582cde0c304f")
TOKEN_STORE = os.environ.get(
    "EXPLORE_TOKEN_STORE", os.path.join(os.path.expanduser("~"), ".outlook-mcp-tokens.json")
)
MCP_ENV = os.environ.get("EXPLORE_MCP_ENV", r"C:\utils\outlook-mcp\.env")

HERE = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_PATH = os.path.join(HERE, "..", "pipeline", "data", "overrides.json")
CANDIDATES_PATH = os.path.join(HERE, "pending-additions.json")

# SharePoint column -> feature property (only set when the submitter gave a value)
FIELD_MAP = [
    ("NewName", "name"),
    ("NewAddress", "address"),
    ("NewPhone", "phone"),
    ("NewWebsite", "website"),
    ("NewHours", "hours"),
    ("NewCategory", "category"),
]


# --- pure transforms (reused by the future repository_dispatch Action) -------

def parse_coordinates(text: str | None) -> list[float] | None:
    """Parse the form's "lat,lng" into GeoJSON [lng, lat]; None if absent/bad."""
    if not text or "," not in text:
        return None
    try:
        lat_s, lng_s = text.split(",", 1)
        lat, lng = float(lat_s.strip()), float(lng_s.strip())
    except ValueError:
        return None
    # sanity: Burton sits near (43.0, -83.6); reject obviously swapped/garbage pairs
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return [lng, lat]


def _why(row_id: str, change_type: str) -> str:
    return (
        f"Business-submitted change (queue row {row_id}, {change_type}), approved by IT "
        f"{date.today().isoformat()}; submitter contact verified on file (not published)."
    )


def row_to_override(fields: dict) -> tuple[str, dict] | None:
    """Convert an Approved queue row into an overrides.json (id, entry) pair.

    Returns None for rows this tool does not auto-apply (add-new, or rows
    missing a listing id).
    """
    change = fields.get("ChangeType", "")
    listing_id = (fields.get("ListingId") or "").strip()
    row_id = str(fields.get("id", "?"))
    if change == "Add my business" or not listing_id:
        return None

    entry: dict = {}
    if change == "Permanently closed":
        entry["hidden"] = True
        entry["_why"] = _why(row_id, change)
        return listing_id, entry

    for col, prop in FIELD_MAP:
        val = (fields.get(col) or "").strip()
        if val:
            entry[prop] = val
    coords = parse_coordinates(fields.get("NewCoordinates"))
    if coords:
        entry["coordinates"] = coords
    elif change == "Moved":
        # address changed but no pin: the pipeline does NOT re-geocode overridden
        # records, so flag for a manual coordinate before this is fully correct.
        entry["_todo"] = "NEEDS COORDINATES: moved without a pin -- geocode the new address."
    if not any(k for k in entry if not k.startswith("_")):
        return None  # nothing usable was submitted
    entry["_why"] = _why(row_id, change)
    return listing_id, entry


def row_to_candidate(fields: dict) -> dict:
    """Convert an Approved add-new row into a facilities.geojson candidate
    feature (geometry null -> the pipeline geocodes the address)."""
    row_id = str(fields.get("id", "?"))
    name = (fields.get("Title") or "").strip()
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    props = {"name": name}
    for col, prop in FIELD_MAP:
        val = (fields.get(col) or "").strip()
        if val and prop != "name":
            props[prop] = val
    coords = parse_coordinates(fields.get("NewCoordinates"))
    return {
        "type": "Feature",
        "id": f"burton:{slug}",
        "geometry": {"type": "Point", "coordinates": coords} if coords else None,
        "properties": props,
        "_review": (
            f"Queue row {row_id}: VET BEFORE PASTING into facilities.geojson -- "
            "dedup against existing OSM/Overture records, confirm the category is one "
            "the app knows, confirm the address is inside the city. Delete this _review key."
        ),
    }


def apply_rows(rows: list[dict], overrides: dict) -> dict:
    """Fold Approved rows into the overrides dict (mutates + returns a report)."""
    report = {"applied": [], "candidates": [], "skipped": []}
    for row in rows:
        fields = row.get("fields", row)
        change = fields.get("ChangeType", "")
        if change == "Add my business":
            report["candidates"].append(row_to_candidate(fields))
            continue
        result = row_to_override(fields)
        if result is None:
            report["skipped"].append(
                f"row {fields.get('id', '?')}: no listing id or no usable fields"
            )
            continue
        listing_id, entry = result
        if listing_id in overrides:
            overrides[listing_id].update(entry)
        else:
            overrides[listing_id] = entry
        report["applied"].append(f"row {fields.get('id', '?')} -> {listing_id}")
    return report


# --- file writers (shared by the on-demand + payload paths) ------------------

def _write_overrides(overrides: dict) -> None:
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _merge_candidates(new_cands: list[dict]) -> None:
    """Merge add-new candidates into pending-additions.json, dedup by id. The
    payload path applies one row at a time, so it must MERGE (not overwrite like
    the batch on-demand run) to preserve candidates awaiting manual vetting."""
    existing: dict = {"candidates": []}
    if os.path.exists(CANDIDATES_PATH):
        try:
            with open(CANDIDATES_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, ValueError):
            existing = {"candidates": []}
    by_id = {c.get("id"): c for c in existing.get("candidates", [])}
    for c in new_cands:
        by_id[c.get("id")] = c
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump({"candidates": list(by_id.values())}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def run_from_payload(payload: dict) -> int:
    """Apply ONE approved row delivered via a repository_dispatch client_payload
    (the approval-triggered Action path, #66). Reuses the same pure transforms as
    the on-demand run; NO Graph token -- the flow pushed the fields in the payload
    and marks the SharePoint row Applied itself after the dispatch returns."""
    if "id" not in payload:
        payload["id"] = payload.get("ID", "dispatch")
    with open(OVERRIDES_PATH, encoding="utf-8") as f:
        overrides = json.load(f)
    report = apply_rows([payload], overrides)
    for line in report["applied"]:
        print(f"  apply   {line}")
    for cand in report["candidates"]:
        print(f"  vet     add-new candidate {cand['id']}")
    for line in report["skipped"]:
        print(f"  skipped {line}")
    if report["applied"]:
        _write_overrides(overrides)
        print(f"Wrote {OVERRIDES_PATH}")
    if report["candidates"]:
        _merge_candidates(report["candidates"])
        print(f"Merged {len(report['candidates'])} candidate(s) into {CANDIDATES_PATH}")
    if not report["applied"] and not report["candidates"]:
        print("No change applied (no usable fields / no listing id).")
    return 0


# --- Graph I/O ---------------------------------------------------------------

def _load_env(path: str) -> dict:
    """Minimal .env parser (KEY=VALUE lines); values never printed."""
    out: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def get_graph_token() -> str:
    env = {**_load_env(MCP_ENV), **os.environ}
    client_id = env.get("MS_CLIENT_ID") or env.get("OUTLOOK_CLIENT_ID")
    if not client_id:
        sys.exit("FAIL: no MS_CLIENT_ID (is the outlook-mcp .env present?)")
    with open(TOKEN_STORE, encoding="utf-8") as f:
        tokens = json.load(f)
    if not tokens.get("refresh_token"):
        sys.exit("FAIL: no refresh token -- authenticate the outlook-mcp first")
    body = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": tokens["refresh_token"],
        "scope": "https://graph.microsoft.com/.default offline_access",
    }
    if env.get("MS_CLIENT_SECRET"):
        body["client_secret"] = env["MS_CLIENT_SECRET"]
    tenant = env.get("MS_TENANT_ID", "common")
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=urllib.parse.urlencode(body).encode(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        parsed = json.load(resp)
    if parsed.get("refresh_token"):
        tokens["refresh_token"] = parsed["refresh_token"]
        with open(TOKEN_STORE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
    return parsed["access_token"]


def graph(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0{path}",
        data=json.dumps(payload).encode() if payload else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode()
    return json.loads(text) if text else {}


def fetch_approved(token: str) -> list[dict]:
    path = (
        f"/sites/{SITE}:/lists/{LIST_ID}/items"
        "?$expand=fields&$top=200&$filter=" + urllib.parse.quote("fields/Status eq 'Approved'")
    )
    items = graph(token, "GET", path).get("value", [])
    # carry the SharePoint item id into fields for _why provenance
    for it in items:
        it.setdefault("fields", {})["id"] = it.get("id")
    return items


def mark_applied(token: str, item_id: str) -> None:
    graph(
        token,
        "PATCH",
        f"/sites/{SITE}:/lists/{LIST_ID}/items/{item_id}/fields",
        {"Status": "Applied", "AppliedDate": date.today().isoformat()},
    )


def main() -> int:
    if "--payload-file" in sys.argv:
        # Approval-triggered Action path (#66): apply one row from a dispatch payload.
        path = sys.argv[sys.argv.index("--payload-file") + 1]
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        return run_from_payload(payload)

    dry = "--dry-run" in sys.argv
    token = get_graph_token()
    rows = fetch_approved(token)
    if not rows:
        print("Nothing to apply: no rows with Status=Approved.")
        return 0

    with open(OVERRIDES_PATH, encoding="utf-8") as f:
        overrides = json.load(f)
    report = apply_rows(rows, overrides)

    print(f"{len(rows)} approved row(s):")
    for line in report["applied"]:
        print(f"  apply   {line}")
    for cand in report["candidates"]:
        print(f"  vet     add-new candidate {cand['id']} -> {CANDIDATES_PATH}")
    for line in report["skipped"]:
        print(f"  skipped {line}")

    if dry:
        print("\nDRY RUN: no files written, no rows marked Applied.")
        return 0

    if report["applied"]:
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\nWrote {OVERRIDES_PATH}")
    if report["candidates"]:
        with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
            json.dump({"candidates": report["candidates"]}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Wrote {CANDIDATES_PATH} -- vet + paste into facilities.geojson by hand")

    for row in rows:
        fields = row.get("fields", {})
        # candidates stay Approved until manually pasted; applied/skipped-with-no-data
        # rows are closed out so they do not re-apply forever.
        if fields.get("ChangeType") != "Add my business":
            mark_applied(token, row["id"])
    print("Rows marked Applied (add-new candidates stay Approved until vetted).")
    print("\nNEXT: python pipeline/run.py  ->  review the git diff  ->  commit + push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
