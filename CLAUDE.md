# Explore Burton MI -- Public Interactive City Map

Public static site (Vite + Svelte + Leaflet) with 23 civic dashboards, Resident Guide, PWA + offline support, and native Android app (Google Play internal testing). Deployed at `https://explore.burtonmi.gov` (GitHub Pages).

## Status

**Soft-launch live** (gate: `?unlock=` bypass, noindex). Web: 279 vitest tests, 0 Svelte warnings, build clean. **Android v1.14+** (vc23): push notifications, widget refresh, deep links, offline badge, native quick-actions row. Refactor #84 (tools/lib migration) MERGED and COMPLETE; Dependabot 0 open alerts. Native app on Play internal track; iOS wrapper compiles in CI (not published).

## Architecture

- **Web:** Vite dev server (`npm run dev`); built to `dist/` and deployed to GitHub Pages via `deploy.yml` workflow.
- **Mobile:** Capacitor (native Android wrapper); Firebase for push (project `exploreburton`); keyless WIF releases to Play.
- **Data pipeline:** Python at `pipeline/` (own venv); generates `public/*.json` data files committed to repo; web fetches lazy on component init.
- **Intake flows:** Power Automate on `make.gov.powerautomate.us` (GCC tenant, gov.api.flow endpoints); SharePoint lists on `/sites/ITDepartment`.

## Key Commands

**Web dev/build:**

```bash
npm run dev                              # Vite dev server, localhost:5173
npm run build                            # Production build -> dist/
npm run check                            # svelte-check + tsc
npm run test                             # vitest run
npm run test:watch                       # Watch mode
```

**Data pipeline:**

```powershell
# From pipeline/ folder, use the committed venv:
.venv\Scripts\python.exe -m pytest test tools -q  # Run pytest (279 pass)
.venv\Scripts\python.exe tools/build_address_points.py
.venv\Scripts\python.exe tools/extract_paser.py
.venv\Scripts\python.exe tools/capital_roads_link.py
```

## Critical Gotchas

**Crime dashboard quarantine:** `feature/crime-dashboard-hold` branch NEVER push to main without explicit city buy-in. Crime data lives on a local-only branch for review only.

**Schools data:** Per-district only (never sum city-wide). Rollup would misrepresent residents per district.

**API keys in user env vars:** FCC_BROADBAND_API_KEY, CENSUS_API_KEY, DATA_GOV_API_KEY live in Windows user environment variables (setx), never committed to git. New sessions inherit them. Missing keys cause silent data gaps (datasets fetch empty), not errors.

**Soft-launch gate:** `/` checks `config.softLaunchGate.active` + `?unlock=` query param. Native app exempt via `config.nativeAppExempt`. Change gate state in `public/config.json`.

**CSP headers:** Content-Security-Policy deployed to Cloudflare as Report-Only; user must rename to enforcement + add WAF bot-skip rule for native app (fetch JSON, cannot solve challenges).

## Data Gotchas

- Address points from BS&A Assessing situs (not owner; do not sum city-wide). Built via `Extract-BurtonAddressPoints.ps1` (external) + `tools/build_address_points.py` (repo).
- Capital projects transcribed from budget book; roads tie-in via `capital_roads_link.py`.
- Zoning overlay 2017 (refresh from source DWG/shapefile pending #44).
- Overture Maps layer auto-deduped (120m) and excludes residential categories (false-positive filter at `overture.exclude_categories`).

## Planning

- Read `planning/STATE.md` at session start.
- Refactoring plan: `docs/REFACTORING_PLAN.md` (gitignored, internal).
- All web changes: branch off main, FF-merge, push triggers Pages deploy.
- Python changes on same branch regenerate and diff to verify byte-identical outputs.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:

- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
