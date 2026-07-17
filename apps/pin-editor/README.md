# Burton Pin Editor

A local, single-user map tool to manage the Explore Burton business list -- **add, move,
delete, and edit** every pin (name, category, address, phone, website, hours) -- writing the
pipeline's source files, regenerating `public/data.geojson`, and publishing with one click.

Runs only on your machine at **<http://pins.local>**. It is never deployed (the public site
only publishes `dist/`).

## Setup (once)

Double-click **`setup.cmd`**. It:

1. creates a Python virtual environment and installs dependencies,
2. adds `127.0.0.1 pins.local` to your Windows hosts file (an elevation prompt appears),
3. warns if port 80 is already in use.

If port 80 is taken, start with another port and use that in the URL:

```text
set PIN_EDITOR_PORT=8080
run.cmd
# then open http://pins.local:8080
```

If `pins.local` does not resolve, use `http://127.0.0.1` instead (same app).

## Run

Double-click **`run.cmd`** (or `.venv\Scripts\python.exe app.py`). It opens
<http://pins.local> and starts the server. Ctrl+C to stop.

## How it works

- Each pin's id prefix decides where an edit is written:
  - **Curated** (`burton:` city facilities, `manual:` pins you add) -> `pipeline/data/facilities.geojson`.
  - **Auto-discovered** (`osm:`, `overture:`) -> `pipeline/data/overrides.json` (a coordinate,
    a field, or `hidden: true`). The discovered pins are regenerated each pipeline run, so they
    are corrected via overrides rather than edited in place.
- Edits accumulate in the **Pending changes** tray and only touch disk on **Save & regenerate**,
  which writes the source files then runs `pipeline/run.py` to rebuild `data.geojson`.
- **Publish** commits only the four allowlisted source/generated data files and pushes the
  current review branch. It refuses to run if an unrelated file is already staged, and it
  runs gitleaks plus a public-data PII check against the exact staged diff before committing.
  Open a pull request and merge it after review; the protected `main` branch then triggers
  the normal GitHub Pages deploy. Publish never force-pushes.

## Excel export / import (delegating edits)

For bulk edits, or to hand the work to someone else, use the **Export** and **Import**
buttons in the top bar.

- **Export** downloads `burton-pins.xlsx` -- one row per pin, with a category dropdown and
  a `delete` yes/no column. The `id` and `source` columns are the keys; leave them alone.
- Edit in Excel (or Excel Online -- share the file, they edit, send it back). To **add** a
  pin, add a row, leave `id` blank, and fill `name`, `category`, `lat`, `lng`. To **remove**
  a pin, set its `delete` column to `yes`.
- **Import** the edited file. The tool diffs it against the current pins and drops the
  changes into the **Pending changes** tray for review (same as manual edits) -- nothing is
  written until you Save. A row simply *missing* from the sheet is left alone (only the
  `delete` column removes a pin), so a partial sheet can never wipe data. Invalid categories
  or new rows missing name/coords are reported as warnings and skipped. Imports are limited
  to 10 MiB and malformed-workbook details stay in the local server log.

This keeps the tool single-user (you run it locally and do the import) while letting a
colleague do fieldwork in a spreadsheet.

## Notes

- Regeneration uses **cached** OSM/Overture data (no network). On a fresh clone where the cache
  is missing, run the pipeline once with a refresh first:
  `cd ../../pipeline && .venv\Scripts\python.exe run.py --refresh`.
- Install `gitleaks` before publishing; the publish preflight fails closed if it is missing.
- Publish pushes whatever branch the repo is on. Use a review branch, not `main`, then open a
  pull request so required checks and approval can run.
- This tool edits real repo files. Everything is in git, so any edit is recoverable with
  `git checkout -- pipeline/data public/data.geojson`.

## Tests

```text
.venv\Scripts\python.exe -m pytest
```

`edits.py` (the edit-to-source-file routing) is covered by `test/test_edits.py`; the
newline-preserving file writes by `test/test_store.py`.
