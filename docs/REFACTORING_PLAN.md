# ExploreBurtonMI — Refactoring & Improvement Plan

> **2026-07-17 status:** This historical whole-codebase plan contains snapshot
> details that have since been implemented or become stale. For current work on
> the map, dashboards, and Resident Guide, use the security-first plans in
> `planning/specs/2026-07-17-*-refactor-plan.md` and the companion comprehensive
> security audit. Retain this document as background; do not execute its old
> line counts, CI assumptions, or file paths without re-verification.
>
> Produced 2026-07-06 from a four-track parallel review of the codebase
> (Svelte components · TypeScript modules & tests · Python pipeline/tools ·
> build/CI/data payloads). Every finding below carries file:line references
> that were verified against the working tree at the time of review.
>
> **How to use this document:** work the phases in order. Each task is written
> to be self-contained enough to hand to a junior engineer or a low-cost
> AI agent (see "Execution notes" at the end). Effort: S = under ~1 h,
> M = half a day, L = 1–3 days. Impact reflects user-facing or
> reliability value, not code aesthetics.

---

## Codebase snapshot (verified)

- **Frontend:** Svelte 5 + Vite + TypeScript PWA, ~9,900 lines under `src/`.
  Fully migrated to runes — zero instances of `export let`, `$:`,
  `createEventDispatcher`, `svelte/store`, or legacy `on:` directives.
  No dead components. Capacitor 8 wraps it for Android/iOS.
- **Data layer:** ~536 KB `public/data.geojson` + ~524 KB
  `public/address-points.json` fetched eagerly on boot; 12+ overlay
  GeoJSON files (zoning 316 KB, flood 284 KB, …) toggled from `config.json`.
- **Pipeline:** `pipeline/` (curated merge/validate/emit with a strong
  fail-loud `validate.py`) plus ~34 standalone `tools/extract_*/fetch_*/build_*`
  scripts and a separate Flask app in `tools/pin-editor/`.
- **Tests:** 28 vitest files (run in CI), 23 Python test files
  (**never run in CI**).
- **CI:** 6 workflows. `deploy.yml` runs `npm test` + `npm run build` only —
  no `npm run check`, no pytest, and **no workflow triggers on pull requests**.

What is already good (leave alone, use as templates):

- `pipeline/src/validate.py` — fail-loud allowlist gate; the model for
  everything in Workstream D.
- `pipeline/src/util.py` — clean `http_get_json`/`http_post_json`
  (requests + timeout + `raise_for_status`); underused, not broken.
- `charts/scale.ts`, `ChartTip.svelte`, `panelCsv.ts` — correctly shared
  across all chart components.
- `DashboardMenu.svelte` — reference-quality a11y (roving tabindex,
  aria-expanded, focus restore); template for the shared Modal.
- Firebase/push is correctly lazy-loaded only on native
  (`src/main.ts:32`); keystores/`google-services.json` correctly
  gitignored and injected from CI secrets.

---

## Phase 0 — Safety nets (do first; everything else depends on these)

These are small, independent, and remove the risk of every later refactor.

### 0.1 Make CI actually gate changes — Effort S · Impact very high

`deploy.yml:38-44` runs `npm ci && npm test && npm run build` only.

- Add `npm run check` (svelte-check + tsc) as a step before `npm test`
  in `deploy.yml`. Today a type error ships straight to production.
- Add a pytest step to `apply-listing.yml` **before** `python pipeline/run.py`
  (line 51): `pip install -r pipeline/requirements.txt -r tools/requirements.txt
  && pytest pipeline/test tools -q`. This workflow auto-applies listing data
  and currently has zero regression protection despite 23 test files existing.
- Add a new `ci.yml` triggered on `pull_request` running: `npm run check`,
  `npm test`, `npm run build`, and the pytest suite. Nothing runs on PRs
  today — contributions land on `main` before any test executes.
- (Optional, S) Add a `pin-editor` pytest job (needs its own
  `tools/pin-editor/requirements.txt` install).

### 0.2 Delete or rewrite `SPEC.md` — Effort S · Impact high

`SPEC.md` (dated 2026-06-03) describes the repo as an unmodified 2017
Code-for-Boston "Finda" fork on RequireJS/Twitter Flight with Boston data.
The actual app is a fully custom Svelte 5 + Capacitor PWA with a Python ETL
pipeline. Anyone reading it first builds a wrong mental model. `README.md`
is accurate — delete `SPEC.md` or reduce it to a pointer at README.

### 0.3 Fix the `About.svelte` backdrop-click bug — Effort S · Impact med

`src/lib/About.svelte:25` — `onclick={closeAbout}` on the backdrop lacks the
`e.target === e.currentTarget` guard every sibling modal has
(`Settings.svelte:66`, `WelcomeModal.svelte:67-69`, `ReportIssue.svelte:206-208`…).
Clicking anything inside the dialog (e.g. a credit link) closes it. One-line fix;
superseded later by the shared Modal (1.1) but worth fixing now.

### 0.4 Empty-result guard in `extract_transit.py` — Effort S · Impact med-high

`tools/extract_transit.py:140-184` writes `transit-routes.geojson`/bus stops
unconditionally. Every sibling extractor bails on empty results
(`extract_flood.py:93-94`, `extract_zoning.py:82-83`, …). A GTFS schema change
silently ships an empty bus overlay to the public map. Add
`if not features: raise SystemExit(...)` before each write.

---

## Phase 1 — Frontend consolidation (highest-value refactor)

### 1.1 Shared `Modal.svelte` — Effort M · Impact high (a11y + ~400 dup lines)

Six dialogs each hand-roll backdrop + `role="dialog"` + Escape +
`registerOverlay` + close button with duplicated CSS:
`About.svelte:21-59`, `Settings.svelte:64-105`, `WelcomeModal.svelte:62-94`,
`Lightbox.svelte:36-53`, `SuggestEdit.svelte:137-146`, `ReportIssue.svelte:201-210`.

Focus management is inconsistent and partly broken:

- `WelcomeModal`, `Lightbox`, `Settings`, `Detail` save/restore `lastFocus` correctly.
- `SuggestEdit.svelte:49-63` focuses in but never restores focus on close.
- `ReportIssue.svelte` does **neither** — a keyboard user who opens
  "Report an issue" is left focused on the button behind the backdrop.
- **No dialog has a focus trap**; Tab escapes into background content in all six.

Plan:

1. Build `src/lib/Modal.svelte` (props: `open`, `label`/`labelledby`;
   snippets for header/body) owning: backdrop with target-guard click-close,
   Escape, `registerOverlay` wiring, focus save → move-in → restore,
   and a focus trap (or `inert` on the app root while open).
   Use `DashboardMenu.svelte` as the a11y reference.
2. Migrate the six dialogs one per commit, starting with `ReportIssue`
   (worst a11y) and `About` (has the click bug).
3. Extract the shared form-field CSS (`SuggestEdit.svelte:290-497` vs
   `ReportIssue.svelte:344-592` are ~90 % identical) into a `.civic-form`
   stylesheet or `FormField.svelte`, and the duplicated post-submit
   "copy tracking link" block into `TrackLinkPanel.svelte`.

### 1.2 Decompose `Map.svelte` (913 lines) — Effort L · Impact high

Six concerns in one file. Extract in this order (each is independently shippable):

1. `src/lib/map/dataLayers.ts` — the `config.dataLayers`/`imageOverlays`
   block (lines ~339-529, largest chunk, ~190 lines).
2. `src/lib/map/clusterPreview.ts` — `bindClusterPreview`/`openClusterPreview`
   (lines ~133-192, pure Leaflet, no component state).
3. `src/lib/map/geolocation.ts` — `applyUserLocation`/`locateNative`/`locateMe`
   (lines ~44-120, web + Capacitor branches).
4. Leave only map lifecycle + the `$effect`s that must live in the component.

While extracting (1), **verify overlay layers are fetched on toggle, not on
mount** — if any of the 12 dataLayers (~670 KB total) load eagerly, make them
lazy in the same change.

### 1.3 App-wide `Icon.svelte` — Effort M · Impact med

The same 8-attribute `<svg viewBox="0 0 24 24" …>{@html …}</svg>` wrapper is
hand-copied in ~10 places (`App.svelte:232-234`, `QuickActions.svelte:57-68`,
`List.svelte:32-34,67-69`, `Search.svelte:25-36`, `Detail.svelte:81-93`,
`guide/OpsStatus.svelte:60-72`, `PushBanner.svelte:30-34`,
`OfflineBadge.svelte:18-29`, `OpenData.svelte:59-63`, `AlertBanner.svelte:76-107`),
with some path data duplicated verbatim against `guide/icons.ts`.
Generalize `guide/GuideIcon.svelte` into `src/lib/Icon.svelte` (name + size)
backed by one icon registry merging `guide/icons.ts` with the ad hoc icons.

### 1.4 Decompose `InfoView.svelte` (616 lines) — Effort M · Impact med-high

Extract `InfoHeader.svelte`, `DashboardNav.svelte` (prev/next, lines 240-255),
and `InfoExplainer.svelte` — the collapsible disclosure appears twice with
copy-pasted markup at lines 176-199 and 201-217 differing only in field names.

### 1.5 Small shared helpers — Effort S each · Impact med

- `loadJson<T>()` rune helper: the same onMount + try/catch + loading/entries
  block appears in `Guide.svelte:17-25`, `guide/WasteSchedule.svelte:12-23`,
  `guide/OpsStatus.svelte:28-40`, `guide/CivicClerkMeetings.svelte:31-44`.
- `createChartHover()` (`.svelte.ts`): identical hover/tooltip positioning in
  `charts/Bars.svelte:11-20`, `charts/Donut.svelte:15-24`,
  `charts/TrendLine.svelte:61-77`.
- `persistedFlag(key)`: the dismiss-once localStorage pattern in
  `ClosureBanner.svelte:13-29`, `InstallPrompt.svelte:19-23`,
  `AlertBanner.svelte:29-44`, `WelcomeModal.svelte:11-16`.

---

## Phase 2 — TypeScript module layer

### 2.1 Kill exact-duplicate logic — Effort S each · Impact high

- **Haversine twice, byte-for-byte:** `src/App.svelte:155-163` duplicates the
  tested `haversineMeters` in `src/lib/reverseGeocode.ts:26-43`. Import the
  tested one; delete the local copy (only one is covered by tests today).
- **Local-today ISO date twice:** `AlertBanner.svelte:50` reimplements
  `closures.ts:42-46`'s `localTodayISO()` — which exists specifically to avoid
  the UTC-rollover bug its comment documents. Reuse it.
- **Site origin in three shapes:** `remote.ts:14` (`REMOTE_BASE`),
  `hash.ts:20` (`SITE_BASE`), `deepLinks.ts:13` (`SITE_HOST`). Keep one
  constant (in `hash.ts`, DOM-free) and derive the others.

### 2.2 Close the validation gap — Effort M · Impact high

`config.ts:20-39` `validateConfig` checks 3 of ~15 required fields then
`return c as AppConfig`; components then blindly destructure
`config.properties` (`Detail.svelte:42`), `config.facets` (`Facets.svelte:21`),
`config.list[0]` (`List.svelte:10-11`), `config.categoryField`
(`Map.svelte:197-199`), `config.search.keys` (`App.svelte:136`). A malformed
`config.json` throws a raw TypeError deep in a component instead of failing
loudly as the module's own comment promises. Extend `validateConfig` to all
required fields; add `validateGuideBundle`/`validateOpsStatusBundle` for the
blind casts at `Guide.svelte:20` and `guide/OpsStatus.svelte:32`, and type the
wire response in `track.ts:65-73`.

### 2.3 Extract pure routing/dashboards from the store — Effort M · Impact high

`store.svelte.ts` (498 lines) mixes reactive UI state with the static dashboard
registry (`DASHBOARD_GROUPS`/`DASHBOARDS`, lines 28-102), pure hash-routing
helpers (`viewFromHash`, `guideSectionFromHash`), theme side effects, install
prompt, and the overlay registry. Extract `src/lib/dashboards.ts` with the
pure parts (registry + `isDashboard`/`dashboardGroupLabel`/`adjacentDashboards`/
`viewFromHash`/`guideSectionFromHash`) so they become unit-testable without
runes. Do **not** split the reactive store further yet — consumers import named
exports cleanly; splitting is preventive only (revisit if it keeps growing).

### 2.4 Untested high-risk modules — Effort S-M each · Impact high

In priority order:

1. `src/lib/remote.ts` (`dataFetch`, 44 lines) — the single fetch path for all
   data loading, with native/web branching, 5 s AbortController timeout, and
   fallback logic. Zero tests. Mock `Capacitor.isNativePlatform()` and cover
   the timeout/fallback branches.
2. `src/lib/comingSoon.ts` (72 lines) — gates the whole public site
   (`shouldGate`/`tryUnlock`); pure, trivially testable, untested.
3. The routing helpers extracted in 2.3 (analogous to already-tested `hash.ts`).
4. `src/lib/search.ts` — asserts on the MiniSearch config behavior
   (fuzzy 0.2, AND, 2-char minimum).

### 2.5 Minor cleanups — Effort S · Impact low

- Silent `.catch(() => {})` on all three native-init imports in
  `src/main.ts:20-34` — log the failure at minimum.
- Straighten the type-import cycle: `types.ts:4-5` imports from
  `templates.ts`/`filter.ts` while both import from `types.ts`. Move
  `PropertyConfig`/`Facets` into `types.ts`; make imports one-way. If
  `types.ts` (420 lines) keeps growing, split by domain
  (config/geo/info-panel/guide) with `types.ts` re-exporting.
- Delete or use the unused export `DEFAULT_MAX_DISTANCE_M`
  (`reverseGeocode.ts:24`); un-export `CITY_BOUNDS` (`report.ts:24`).
- Adopt a `{v: 1, data}` envelope for localStorage before the next breaking
  format change (all readers currently reset-to-default silently).

---

## Phase 3 — Python pipeline & tools shared library

The root cause of most tools/ findings: `pipeline/src/util.py` already has the
right HTTP helpers, but the ~30 `tools/` scripts each reimplement fetching with
raw `urllib`. Build one small shared package and migrate mechanically.

### 3.1 Create `tools/lib/` (or repo-root `scripts_common/`) — Effort M · Impact high

Modules and the duplication they replace:

| Module | Contents | Replaces |
|---|---|---|
| `httpio.py` | `get_json(url, params, attempts=4, timeout=60)` with retry/backoff (promote `fetch_schools.py:141-153`, today the *only* retry logic in the tree) | ~29 scripts' single-shot `urllib.request.urlopen`; ~15 unexplained magic timeouts (30/40/60/90/120/240 s) |
| `arcgis.py` | `paged_query(url, base_params, page_size)` generator | hand-rolled `resultOffset` paging in `extract_flood.py:60-87`, `extract_zoning.py:54-77`, extract_parks/trails/precincts/access (~150 lines) |
| `geo.py` | `round_coords(coords, ndigits=5)` | verbatim copies in `extract_flood.py:33-36`, `extract_zoning.py:48-51`, + ~6 more |
| `paths.py` | `REPO_ROOT`, `public_path()`, `pipeline_data_path()` | the `os.path.abspath(os.path.join(...))` boilerplate in ~30 files |
| `iox.py` | `write_geojson()` (compact), `write_json()` (indent=2), both via **atomic write** (`.tmp` + `os.replace`) | two inconsistent JSON styles (even within `extract_zoning.py`); non-atomic writes everywhere incl. `pipeline/src/emit.py:20-23` — a crash mid-write currently truncates known-good committed JSON |
| `shapecheck.py` | `assert_shape(rows, required_keys)` fail-loud helper modeled on `pipeline/src/validate.py` | nothing — this gap is why a Census column reorder would silently mis-coordinate `build_address_points.py:171-186` |

Migrate scripts in small batches (they're mechanical, independent, and each is
verifiable by diffing regenerated output against the committed JSON).

### 3.2 Dependency hygiene — Effort S · Impact med

- `tools/build_address_points.py:39` imports `requests`, which
  `tools/requirements.txt` doesn't declare (header comment admits it borrows
  the pipeline venv). Add `requests>=2.32`.
- Three pinning philosophies across `pipeline/`, `tools/`, `tools/pin-editor/`
  (loose vs loose vs exact; `requests` pinned two different ways). Pick one
  convention, or document that pin-editor is deliberately strict as a service.

### 3.3 Priority test backfill — Effort M · Impact high

1. `tools/build_publicsafety.py` (293 lines) — `assert_no_pii` at line 227 is
   the only guard between raw fire-department exports and public data, and it
   is untested. Write a red/green test proving it trips on a synthetic address.
2. `tools/apply_dupe_overrides.py` (130 lines) — writes
   `pipeline/data/overrides.json`, which `pipeline/run.py` merges verbatim
   into production data. Untested.
3. `tools/fetch_schools.py` (327 lines, has the retry logic) and
   `tools/build_address_points.py` (256 lines, geocoding). Untested.
The remaining 13 untested one-off scripts are lower priority.

### 3.4 Aggregate skip reporting — Effort S · Impact med

The `fetch_*` dashboard scripts catch-and-skip individual optional metrics
(reasonable per-metric), but `main()` never reports totals — a Census outage
would quietly produce blank charts. Collect skipped metric names and print one
`"N optional metrics skipped: …"` line per run.

### 3.5 Organization — Effort S · Impact low-med

> **Pin-editor move DONE 2026-07-06:** `tools/pin-editor/` -> `apps/pin-editor/`
> (git mv, ci.yml paths updated, `--ignore` flag dropped from the pytest step;
> 38 pin-editor tests pass from the new location). Cache-file + build_guide.mjs
> items still open.

- Move `tools/pin-editor/` (an unrelated Flask app) to `apps/pin-editor/`.
- Move the committed cache files `tools/fire-trends.json` (used by
  `build_fire_trends.py:48`) and `tools/health-acs-trend.json`
  (`fetch_health.py:53`) into a gitignored `tools/.cache/`, matching the
  `pipeline/data/cache/` convention.
- Wrap top-level `readFileSync` calls in `tools/build_guide.mjs` with a
  friendly missing-file error — it runs as `predev`/`prebuild`, so a raw
  ENOENT currently blocks all local dev.

---

## Phase 4 — Performance, PWA, security

### 4.1 Boot payload — Effort M · Impact high

> **RESOLVED 2026-07-06 (partially stale finding):** `address-points.json` is
> NOT fetched on boot — `loadAddressPoints` is called only from ReportIssue's
> pin-drop handler (the #71 lazy loader landed after this review was drafted),
> and the SW precache glob excludes `.json`. Option (c) is already done.
> Options (a)/(b) declined for now; `data.geojson` field-stripping remains
> open if boot cost ever matters.
`data.geojson` (536 KB) + `address-points.json` (524 KB) are fetched
unconditionally in `App.svelte` `start()` on every boot. Options in order of
cheapness: (a) confirm brotli/gzip is actually served at the CDN edge;
(b) strip fields from `data.geojson` that Map/List/Search don't read, moving
detail-only fields to a lazy per-feature fetch; (c) defer
`address-points.json` until the first feature that needs it (reverse geocode /
report flow) rather than boot.

### 4.2 Service-worker cache coverage — Effort S · Impact med

`vite.config.ts:46-49` runtime-caching regex omits `zoning`, `parks`,
`bus-stops`, `bridges`, `paser-roads`, `capital-roads`, `trails`,
`school-districts` GeoJSON — those overlays get no offline caching at all.
Replace the hand-rolled alternation with a `\.(geo)?json$` rule scoped to the
site root. Also raise the 40-entry `maxEntries` cap (or split core map data
and dashboard panels into two caches) so LRU eviction can't drop
`data.geojson` in favor of dashboard panels.

### 4.3 Vendor chunking — Effort S · Impact med

No `manualChunks` configured; leaflet + markercluster + minisearch land in the
single entry chunk, so any app-code change busts the browser cache for vendor
code that never changes. Add
`build.rollupOptions.output.manualChunks` splitting those, plus
`chunkSizeWarningLimit` (or a CI dist-size diff) as a regression guard.

### 4.4 Image optimization — Effort S · Impact med (~1.5–2 MB recoverable)

`sharp` is already a devDependency (used for icon gen). Add
`tools/optimize-images.mjs` and run it over: `emterra-recycling.png` (1.2 MB,
1008×1101 — should be WebP/JPEG), `cityofburton_firedeptlogo_nobackground.png`
(408 KB at 3000×3000), `burton-seal.png` (336 KB),
`burton-historical-plat-map.jpg` (340 KB), `pwa-512.png` (212 KB — typical
optimized size is 20–50 KB).

### 4.5 Security posture — Effort M · Impact med

> **RESOLVED 2026-07-06:** CSP shipped both ways — a meta tag in `index.html`
> (browser-verified locally: boot/map/dashboard/guide with zero violations)
> plus a Cloudflare Transform Rule the user applies from `docs/csp-cloudflare.md`
> (start as Report-Only, then enforce; carries `frame-ancestors`). The SAS-URL
> tradeoff is recorded in that same doc.

- **No CSP anywhere** (no meta tag, and GitHub Pages can't set headers). The
  site already fronts Cloudflare — add CSP via a Transform Rule/Worker, or a
  restrictive `<meta>` CSP covering `script-src`/`img-src`/`connect-src` for
  the known tile + insights hosts.
- **`public/config.json:29-32` ships 4 SAS-signed Logic Apps webhook URLs**
  (submit/report/status/alerts) to every client. Accepted tradeoff for a public
  intake form, but record the decision and add server-side throttling/
  validation in the Logic Apps, since the URLs are effectively public
  credentials for those triggers.

### 4.6 Hygiene — Effort S · Impact low

- Delete root `/CNAME` (only `public/CNAME` reaches `dist/`; two copies drift).
- Fix README pipeline instructions mixing Windows (`.venv\Scripts\python`) and
  POSIX syntax; document the dataLayers/addressPoints system README omits.
- Watch `pipeline/data/overture_places.geojson` (1.7 MB committed snapshot)
  for repo-size growth; consider LFS if refreshes become regular.

---

## Sequencing & dependencies

```text
Phase 0 (all four tasks, independent)          ← do immediately, ~1 day total
   └─ 0.1 CI gates unlock safe refactoring everywhere below
Phase 1: 1.1 Modal → (1.3 Icon, 1.4 InfoView, 1.5 helpers) ; 1.2 Map.svelte independent
Phase 2: 2.1 → 2.2 → (2.3 → 2.4) ; 2.5 anytime
Phase 3: 3.1 lib first → 3.2/3.4 ride along per-script → 3.3 tests → 3.5 anytime
Phase 4: independent of 1–3; 4.2/4.3/4.6 are quick wins, 4.1/4.5 need a decision
```

Suggested first sprint (max value, ~2–3 days): 0.1–0.4, 2.1, 4.2, 4.3, 4.6,
3.2, then start 1.1.

## Execution notes (for delegating to low-cost agents)

- Every task above is scoped to named files with line references — hand a
  single numbered task (not a whole phase) to one agent per branch/commit.
- Mechanical migrations (3.1 script adoption, 1.3 icon swap, 1.1 dialog
  migration) parallelize well: one agent per script/component, verified by
  `npm run check && npm test` or `pytest` — which is why Phase 0.1 must land
  first.
- Pipeline script refactors are verifiable by regenerating output and diffing
  against the committed JSON in `public/` — require that check in each task.
- Do not combine refactors with behavior changes in one commit; the diffs
  above are designed to be no-op for users except where explicitly noted
  (a11y fixes in 1.1, guards in 0.3/0.4).
