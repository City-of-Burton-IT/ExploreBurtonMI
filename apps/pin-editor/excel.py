# Excel export/import diff logic for the pin editor. Pure functions -- no openpyxl,
# no IO. features_to_rows() flattens pins to spreadsheet rows; rows_to_edits() diffs an
# edited sheet against the current pins and produces the same edit ops as the map UI
# (which edits.py then routes to the right source file).
from __future__ import annotations

from edits import is_curated

COLUMNS = ["id", "source", "name", "category", "address", "phone", "website", "hours",
           "lat", "lng", "delete"]
TEXT_FIELDS = ["name", "category", "address", "phone", "website", "hours"]
OPT_FIELDS = ["address", "phone", "website", "hours"]
_TRUE = {"yes", "y", "true", "1", "x"}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _cat(c) -> str:
    """A pin's category may be a list (multi-category pins); render it as one cell."""
    if isinstance(c, list):
        return "; ".join(str(x) for x in c)
    return _s(c)


def _parse_float(v):
    try:
        return float(_s(v))
    except (ValueError, TypeError):
        return None


def features_to_rows(features: list) -> list:
    """Flatten pins to ordered row dicts (one per pin) for the Excel export."""
    rows = []
    for f in features:
        coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
        p = f.get("properties", {})
        rows.append({
            "id": f.get("id", ""),
            "source": "curated" if is_curated(f.get("id", "")) else "discovered",
            "name": p.get("name", "") or "",
            "category": _cat(p.get("category")),
            "address": p.get("address", "") or "",
            "phone": p.get("phone", "") or "",
            "website": p.get("website", "") or "",
            "hours": p.get("hours", "") or "",
            "lat": coords[1],
            "lng": coords[0],
            "delete": "",
        })
    return rows


def rows_to_edits(rows: list, current_features: list, categories, bbox=None):
    """Diff edited rows against the current pins. Returns (edits, warnings).

    Deletion is explicit (the `delete` column) -- a row simply absent from the sheet is
    NOT treated as a delete, so a partial sheet can never wipe pins.
    """
    cur = {}
    for f in current_features:
        coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
        cur[f.get("id")] = {"props": f.get("properties", {}), "coords": coords}
    cats = set(categories)
    edits, warns = [], []

    def out_of_bbox(lng, lat):
        return bool(bbox) and (lng < bbox[0] or lng > bbox[2] or lat < bbox[1] or lat > bbox[3])

    for i, row in enumerate(rows, start=2):   # row 1 is the header
        rid = _s(row.get("id"))
        delete = _s(row.get("delete")).lower() in _TRUE
        name = _s(row.get("name"))
        category = _s(row.get("category"))

        if rid:
            if rid not in cur:
                warns.append(f"Row {i}: unknown id '{rid}' -- ignored.")
                continue
            if delete:
                edits.append({"op": "delete", "id": rid})
                continue
            fields = {}
            for k in TEXT_FIELDS:
                nv = _s(row.get(k))
                ov = _cat(cur[rid]["props"].get(k)) if k == "category" else _s(cur[rid]["props"].get(k))
                if nv == ov:
                    continue
                if k == "category" and nv not in cats:
                    warns.append(f"Row {i}: category '{nv}' is not valid -- left unchanged.")
                    continue
                fields[k] = nv
            if fields:
                edits.append({"op": "edit", "id": rid, "fields": fields})
            lat, lng = _parse_float(row.get("lat")), _parse_float(row.get("lng"))
            ocoords = cur[rid]["coords"]
            if lat is not None and lng is not None and ocoords[0] is not None:
                if abs(lng - ocoords[0]) > 1e-7 or abs(lat - ocoords[1]) > 1e-7:
                    edits.append({"op": "move", "id": rid, "coordinates": [lng, lat]})
                    if out_of_bbox(lng, lat):
                        warns.append(f"Row {i}: moved location is outside the city limits.")
            continue

        # blank id -> a new pin (or a blank row to skip)
        present = any(_s(row.get(k)) for k in
                      ["name", "category", "address", "phone", "website", "hours", "lat", "lng"])
        if not present or delete:
            continue
        lat, lng = _parse_float(row.get("lat")), _parse_float(row.get("lng"))
        if not name or not category:
            warns.append(f"Row {i}: new pin needs a name and category -- skipped.")
            continue
        if category not in cats:
            warns.append(f"Row {i}: category '{category}' is not valid -- skipped.")
            continue
        if lat is None or lng is None:
            warns.append(f"Row {i}: new pin needs lat and lng -- skipped.")
            continue
        fields = {k: _s(row.get(k)) for k in OPT_FIELDS if _s(row.get(k))}
        edits.append({"op": "add", "name": name, "category": category,
                      "coordinates": [lng, lat], "fields": fields})
        if out_of_bbox(lng, lat):
            warns.append(f"Row {i}: new pin is outside the city limits.")

    return edits, warns
