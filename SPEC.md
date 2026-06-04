# ExploreBurtonMI - Code Review & Specification

> Orientation document for the `City-of-Burton-IT/ExploreBurtonMI` fork.
> Written 2026-06-03 after a full read of the source.

## 1. What this actually is

This is **Finda** - an open-source "find-a" civic-data map app built by
**Code for Boston** (Code for America brigade), MIT licensed. Upstream:
`github.com/codeforboston/finda`. Our repo is a **fork that has not yet been
customized** - it is still the original Boston app, just renamed.

The premise (from the upstream readme): *"You have data with locations. Share it
with the world."* You provide:

- a **`data.geojson`** file (a set of point features with properties), and
- a **`config.json`** file (what to show, what to search, what to filter on),

and Finda renders a **searchable, filterable, faceted map** of those points.
No code changes are needed to adapt it to a new dataset - it is config-driven.

It is **100% client-side / static** - HTML + JS + CSS + two data files. There is
**no backend, no database, no server code**. It can be hosted on GitHub Pages,
IIS, S3, or any static web server.

## 2. Current state of the fork (important)

It is an **unmodified clone of the 2017 Boston app**. Nothing is Burton yet:

| Thing | Current value | Needs to become |
|---|---|---|
| Map center (`config.json`) | `42.3725, -71.1266` (Boston) | Burton, MI (~`43.00, -83.62`) |
| `maxBounds` | New England box | A Michigan / Genesee County box |
| `data.geojson` | 323 Boston **youth-services** orgs | A Burton dataset |
| Branding / About | "Code for Boston" | City of Burton |
| Analytics tracker | Code for Boston's Google property | Removed or Burton's |
| Default branch | `gh-pages` (deploy branch); no `master` | n/a |
| Last upstream commit | **2017** | n/a |

So: the fork **runs**, but if deployed today it would show a map of Boston
youth services branded as Code for Boston.

> Note on provenance: GitHub does not register this repo as a fork
> (`parent: null`), so it was likely **imported/pushed** rather than created with
> the Fork button. Upstream is unambiguously `codeforboston/finda` from the
> in-code references. Functionally this makes no difference - just know that
> `git`-level upstream tracking is not wired up.

## 3. Architecture

### 3.1 Tech stack (all 2014-2017 era)

- **RequireJS** (`require.js`) - AMD module loader. Entry point is
  `src/script.js` via `data-main` in `index.html`.
- **Twitter Flight** (`flight.min.js`) - an event-driven component framework
  (abandoned by Twitter ~2015). Components attach to a DOM node and communicate
  **only by triggering/listening to events on `document`** - there is no shared
  state object. This is the single most important thing to understand about the
  codebase.
- **Leaflet** + **Leaflet.markercluster** - the map and point clustering.
- **Fuse.js** - client-side fuzzy full-text search over the dataset.
- **Nominatim / OpenStreetMap** - external address geocoding (the "Locate"
  search box).
- **Handlebars** - HTML templating for popups, list rows, facet widgets.
- **jQuery 1.11**, **lodash**, **Bootstrap 3** - DOM, utilities, layout/modals.
- **Karma + Jasmine + PhantomJS** - tests (a spec exists for nearly every
  component). **Travis CI** on Node 0.10. **JSHint** for linting.
- Build pipeline: **r.js + almond + uglify2 + clean-css** -> `dist/`.

### 3.2 Two layers of components

Total source is small: **~1,400 lines across 17 files.**

**`src/data/*` - no DOM, manage data and logic:**

| File | Role |
|---|---|
| `config.js` | Fetches `config.json`, fires `config` event |
| `geojson.js` | Fetches the geojson, assigns IDs, fires `data` event |
| `search.js` | Address geocoding via Nominatim -> `dataSearchResult` |
| `typeahead.js` | Fuse.js fuzzy search -> `dataTypeaheadResults` |
| `facet.js` | The filtering engine (235 lines, the brain) - computes facet counts and filtered feature-ID sets |
| `analytics.js` | Google Analytics tracking |

**`src/ui/*` - render and capture user input:**

| File | Role |
|---|---|
| `map.js` | Leaflet map, markers, clustering, popups (294 lines, largest) |
| `list.js` | Scrollable sidebar list of results |
| `facet.js` | Renders facet checkboxes; emits `uiFilterFacet` |
| `info.js` | Detail panel when a feature is clicked |
| `search.js` | The address search box |
| `search_results.js` | Typeahead/geocode result dropdown |
| `project.js` | Injects project name/logo/description from config into the page |
| `loading.js` | "Loading..." / "Filtering..." modal |

Plus `infotemplates.js` (formats a feature's properties into popup/detail HTML
based on config) and `timed_with_object.js` (a chunked-iteration helper that
yields to the UI thread so filtering 300+ markers doesn't freeze the browser).

### 3.3 Event flow (the mental model)

```text
script.js attaches all components
        |
config.js  -- fetch config.json --> trigger "config"
        |
   (every component configures itself from config)
        |
geojson.js -- fetch data.geojson --> trigger "data"
        |
   map.js / list.js / facet.js render the dataset

User actions:                    Data layer responds:
  check a facet  -> uiFilterFacet  -> facet.js -> dataFiltered + dataFacets
  type in search -> uiInProgressSearch -> typeahead.js -> dataTypeaheadResults
  press Enter    -> uiSearch       -> search.js (Nominatim) -> dataSearchResult
  click a marker -> selectFeature  -> info.js shows detail, map pans/highlights
  pan/zoom map   -> mapBounds      -> facet.js (if a "map" facet is configured)
```

`dataFiltered` carries a list of `featureIds`; `map.js` and `list.js` both
listen and show/hide accordingly. The whole app is this pub/sub loop.

### 3.4 How config.json drives the UI

- `project` -> name/logo/description/contact (injected by `ui/project.js`)
- `map` -> center, zoom, maxZoom, maxBounds, `preview_attribute` (marker hover label)
- `properties` -> fields shown in the **detail panel**, with formatting hints
  (`url`, `directions`, `title`, list, image)
- `list` -> fields shown in each **sidebar list** row
- `search.full_text.keys` -> which properties Fuse.js searches
- `search.geosearch` -> enables/disables the address search box
- `facets` -> which properties become filters, and the type
  (`list` = match-all, `single` = match-any, `map` = filter by visible map area)
- `analytics` -> see concerns below
- `geojson_source` -> path to the data file

A new dataset that fits the "points with attributes" shape needs **only** a new
geojson + a rewritten config; no JS changes.

## 4. Concerns to address before any Burton deployment

Ordered by priority. These are the real output of this review.

### HIGH - Privacy: phones home to Code for Boston

`config.json` has `analytics.private: false`, and `src/data/analytics.js`
hard-codes `codeForBostonTracker: "UA-37610225-5"`. **Every page view is reported
to Code for Boston's Google Analytics property.** For a municipal site that is an
unacceptable third-party data share. Also `UA-` (Universal Analytics) was **shut
down by Google in July 2023**, so it is broken anyway.
**Fix:** set `analytics.enabled: false` (or `private: true` and strip the CfB
tracker) in config; optionally remove `analytics.js` entirely.

### HIGH - Tracking pixel in the About modal

`index.html` line 75 injects an `<img>` from `http://bostonbuilt.org/icon.php`
on every About-modal view - another third-party phone-home. **Remove that line.**

### HIGH - Mixed content breaks on HTTPS

Several hard-coded `http://` (not `https://`) external URLs will be **blocked as
mixed content** when the site is served over HTTPS (which any city site will be):

- **Map basemap tiles**: `http://korona.geog.uni-heidelberg.de/...`
  (Heidelberg GIScience). This is the actual map background - if it is blocked
  or defunct (likely, given the 2017 commit "update tile provider since acetate
  seems to be defunct"), **the map shows no tiles.** Needs an HTTPS tile source
  (OSM, CARTO, Stadia Maps, or a Burton/Esri source).
- Google Fonts `http://fonts.googleapis.com` (index.html)
- Google Maps directions `http://maps.google.com/maps` (infotemplates.js)

**Fix:** switch all to `https://` and replace the tile provider.

### MEDIUM - Dead/legacy toolchain

Node 0.10, PhantomJS, Karma 0.12, Travis on an EOL runtime, jQuery 1.11,
Bootstrap 3, Flight (abandoned). `npm install` likely will not resolve cleanly on
a modern Node. **The app itself still runs in a browser** (static files), but the
**build and test tooling is effectively unmaintainable** without modernization.
Decision needed: keep it as hand-edited static files, or modernize the stack.

### MEDIUM - Geocoder usage policy

The search box hits public Nominatim. OSM's usage policy requires an identifying
User-Agent and rate-limits heavy use. Fine for low traffic; for a public city
site, consider a dedicated geocoder or disable `geosearch`.

### LOW - The shipped config and data are already out of sync

`config.json` references fields the bundled `data.geojson` does not contain:
`community` (in `search.full_text.keys`) and `services_offered` (in
`properties`) are both **absent from all 323 features** (verified). This is a
residue of the "testing out lgbtq data" commit swapping the dataset under an
older config. Practical takeaway: **do not treat the bundled config/data pair as
a clean reference** - you will rewrite `config.json` to match whatever Burton
dataset you supply anyway, and missing keys fail silently (no error, the field
just does not render).

### LOW - Treat the geojson as trusted operator data

There is no backend, so the only data input is the geojson you ship. Leaf text
values are HTML-escaped by Handlebars (`{{text}}`), so the XSS surface is small,
**but** `url`-type properties render `href="{{url}}"` without scheme validation -
a `javascript:` URL in the data would be live. Since the operator controls the
data file, this is low risk; just do not pipe untrusted/third-party data straight
into the geojson without sanitizing URLs.

### LOW - Data updates are manual

No admin UI. Updating the dataset = regenerate `data.geojson` and redeploy. Fine
for slow-changing data (parks, facilities); poor for frequently-changing data.

## 5. Is it a good fit for Burton?

**Yes, for the right use case.** It is a clean, well-factored, genuinely
config-driven map app with no backend to maintain - cheap to host and adapt. It
suits any **"points on a map + searchable/filterable attributes"** need:

- find-a-park / facility / amenity locator
- polling places
- recycling / yard-waste / leaf-pickup drop sites
- public art, historical markers
- city services directory with addresses

It is **not** suited to routing, parcels/polygons, live data, or anything
needing a logged-in admin.

The main cost is that you are adopting a frozen 2017 codebase: workable as-is
with the HIGH fixes above, but the dev tooling is dead, so ongoing changes mean
hand-editing static files (or a modernization project).

## 6. Suggested path to a Burton-ready app

1. **Run it locally as-is** - serve the folder over HTTP (config/geojson load via
   XHR, so `file://` will not work). Confirm it boots. *(Expect a blank basemap
   due to the dead tile provider - that is the HIGH fix, not a real failure.)*
2. **Decide the dataset / use case** - this drives everything else. *(Open
   question for you.)*
3. **Rebrand & re-center** - `config.json` project/center/bounds, swap
   `img/logo.png`, rewrite the About modal, strip CfB analytics + bostonbuilt
   pixel.
4. **Fix external deps for HTTPS** - new HTTPS tile provider, https fonts/links.
5. **Supply the Burton geojson** - and define `properties` / `facets` /
   `search.full_text.keys` to match its fields.
6. **(Optional) Modernize** - replace Flight/RequireJS/PhantomJS, or accept
   static-file maintenance.

## 7. Open questions for the user

- What **dataset / use case** is this fork for? (Determines all config + data work.)
- **Modernize the stack**, or keep it as minimally-edited static files?
- Where will it be **hosted** - GitHub Pages, `appservices.burton.local` (IIS),
  or elsewhere? (Affects the HTTPS/mixed-content work.)
