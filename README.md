# Explore Burton

A public map of City of Burton businesses, government facilities, and services.
Browse a clustered map, filter by category, and search - all client-side.
Live at <https://explore.burtonmi.gov>.

## Stack

100% static single-page app - no backend.

- [Vite](https://vite.dev/) + [Svelte 5](https://svelte.dev/) + TypeScript
- [Leaflet](https://leafletjs.com/) + markercluster (map + clustering)
- [MiniSearch](https://github.com/lucaong/minisearch) (client-side search)
- [CARTO](https://carto.com/) basemap tiles (HTTPS)

## Develop

```sh
npm install
npm run dev      # local dev server (http://localhost:5173)
npm run check    # svelte-check + tsc type-check
npm test         # vitest unit tests (filter + templates + validation)
npm run build    # production build -> dist/
npm run preview  # serve the production build locally
```

## How it works

The app is **config-driven**: edit [`public/config.json`](public/config.json)
and supply [`public/data.geojson`](public/data.geojson) - no code changes needed
to adapt it to a new dataset.

- `config.json` - map center/bounds/tiles, branding, categories, detail-panel
  fields, facets, and search keys.
- `data.geojson` - the point features (each with `properties`).

## Business / POI data (Overture Maps)

The open business/POI layer comes from the **Overture Maps Foundation** Places
theme (CDLA-Permissive 2.0 -- redistributable with attribution), alongside
OpenStreetMap and curated City of Burton facility records -- all sources the City
is free to publish.

The Overture readers are heavy binary dependencies, so they live in an
**out-of-band extract tool** -- never in the pure-Python pipeline. Refresh
workflow:

```sh
# one-time, in a tools venv:
pip install -r tools/requirements.txt

# extract a fresh Burton-bbox snapshot (commits to pipeline/data/overture_places.geojson):
python tools/extract_overture.py

# REVIEW the snapshot diff, then rebuild + review the public output:
cd pipeline
.venv/bin/python run.py   # Windows: .venv\Scripts\python run.py
```

The pipeline reads the committed snapshot like any curated input and maps Overture
categories to Burton categories via `pipeline/overture_category_map.json`. If the
snapshot is absent, the pipeline runs with OSM + curated facilities only. When the
first snapshot ships, add "(c) Overture Maps Foundation" to the viewer attribution
in `public/config.json` and the About modal.

Source layout (`src/lib/`):

| File | Role |
|---|---|
| `config.ts` / `data.ts` | Load + validate config and GeoJSON (fail loud) |
| `filter.ts` | **Pure** filtering + facet-count engine (unit-tested) |
| `templates.ts` | Format detail fields + URL-scheme validation (unit-tested) |
| `search.ts` | MiniSearch index wrapper |
| `store.svelte.ts` | Shared reactive state (selection, facets, query) |
| `Map / List / Facets / Detail / Search / About .svelte` | UI components |

## Hosting

Targeting GitHub Pages at **explore.burtonmi.gov** (custom domain; `public/CNAME`
set). Any static host works (IIS, CDN, etc.).

## Credits

A ground-up modern rebuild inspired by the open-source
[Finda](https://github.com/codeforboston/finda) app by Code for Boston (MIT).
See [`license.md`](license.md). Map data (c) OpenStreetMap contributors, (c) CARTO.
