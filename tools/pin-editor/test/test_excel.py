# Tests for the Excel export/import diff logic (pure, no openpyxl IO).
from excel import features_to_rows, rows_to_edits

CATS = ["Government", "Dining", "Retail & Shopping"]
BBOX = (-83.85, 42.85, -83.40, 43.15)


def _feat(fid, name, cat, lng, lat, **props):
    return {
        "type": "Feature", "id": fid,
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"name": name, "category": cat, **props},
    }


def _row(**kw):
    base = {c: "" for c in
            ["id", "source", "name", "category", "address", "phone", "website", "hours", "lat", "lng", "delete"]}
    base.update(kw)
    return base


# ---- export ----------------------------------------------------------------

def test_features_to_rows_splits_source_and_coords():
    feats = [
        _feat("burton:city-hall", "City Hall", "Government", -83.616, 42.999, phone="x"),
        _feat("overture:abc", "Cafe", "Dining", -83.62, 42.99),
    ]
    rows = features_to_rows(feats)
    assert rows[0]["id"] == "burton:city-hall"
    assert rows[0]["source"] == "curated"
    assert rows[0]["lat"] == 42.999 and rows[0]["lng"] == -83.616
    assert rows[0]["phone"] == "x"
    assert rows[1]["source"] == "discovered"


# ---- import: existing pins -------------------------------------------------

def _current():
    return [
        _feat("burton:city-hall", "City Hall", "Government", -83.616, 42.999, phone="old"),
        _feat("overture:abc", "Cafe", "Dining", -83.62, 42.99),
    ]


def test_unchanged_rows_produce_no_edits():
    rows = features_to_rows(_current())
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    assert edits == [] and warns == []


def test_field_change_emits_edit():
    rows = features_to_rows(_current())
    rows[0]["phone"] = "(810) 555-1212"
    edits, _ = rows_to_edits(rows, _current(), CATS, BBOX)
    assert {"op": "edit", "id": "burton:city-hall", "fields": {"phone": "(810) 555-1212"}} in edits


def test_coord_change_emits_move():
    rows = features_to_rows(_current())
    rows[1]["lat"] = 42.991
    edits, _ = rows_to_edits(rows, _current(), CATS, BBOX)
    moves = [e for e in edits if e["op"] == "move"]
    assert moves and moves[0]["id"] == "overture:abc"
    assert moves[0]["coordinates"] == [-83.62, 42.991]


def test_delete_flag_emits_delete():
    rows = features_to_rows(_current())
    rows[1]["delete"] = "yes"
    edits, _ = rows_to_edits(rows, _current(), CATS, BBOX)
    assert {"op": "delete", "id": "overture:abc"} in edits


def test_missing_row_is_not_a_delete():
    rows = [features_to_rows(_current())[0]]   # only city-hall present
    edits, _ = rows_to_edits(rows, _current(), CATS, BBOX)
    assert all(e["op"] != "delete" for e in edits)


def test_invalid_category_on_edit_warns_and_drops_it():
    rows = features_to_rows(_current())
    rows[0]["category"] = "Not A Category"
    rows[0]["phone"] = "(810) 555-0000"
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    edit = next(e for e in edits if e["op"] == "edit")
    assert "category" not in edit["fields"]      # invalid category dropped
    assert "phone" in edit["fields"]             # valid change kept
    assert warns                                 # warned about the bad category


def test_unknown_id_warns_and_is_ignored():
    rows = [_row(id="osm:node/999", name="Ghost", category="Dining", lat="42.99", lng="-83.62")]
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    assert edits == [] and warns


# ---- import: new pins ------------------------------------------------------

def test_blank_id_row_emits_add():
    rows = [_row(name="New Diner", category="Dining", lat="42.99", lng="-83.62", phone="x")]
    edits, _ = rows_to_edits(rows, _current(), CATS, BBOX)
    add = next(e for e in edits if e["op"] == "add")
    assert add["name"] == "New Diner" and add["category"] == "Dining"
    assert add["coordinates"] == [-83.62, 42.99]
    assert add["fields"]["phone"] == "x"


def test_blank_row_is_skipped_silently():
    rows = [_row()]
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    assert edits == [] and warns == []


def test_new_row_missing_name_warns_and_skips():
    rows = [_row(category="Dining", lat="42.99", lng="-83.62")]
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    assert edits == [] and warns


def test_multi_category_pin_exports_joined_and_unchanged_is_noop():
    feats = [_feat("overture:big", "Big Box", ["Grocery & Food", "Retail & Shopping"], -83.62, 42.99)]
    rows = features_to_rows(feats)
    assert rows[0]["category"] == "Grocery & Food; Retail & Shopping"
    # round-trip unchanged -> no edit (the joined string equals the list's rendering)
    edits, warns = rows_to_edits(rows, feats, CATS, BBOX)
    assert edits == [] and warns == []
    # changing it to a single valid category -> one edit
    rows[0]["category"] = "Dining"
    edits, _ = rows_to_edits(rows, feats, ["Dining"], BBOX)
    assert {"op": "edit", "id": "overture:big", "fields": {"category": "Dining"}} in edits


def test_out_of_city_add_warns_but_still_adds():
    rows = [_row(name="Far Away", category="Dining", lat="44.0", lng="-85.0")]
    edits, warns = rows_to_edits(rows, _current(), CATS, BBOX)
    assert any(e["op"] == "add" for e in edits)
    assert warns                                  # out-of-bbox warning
