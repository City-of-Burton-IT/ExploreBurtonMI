# Dashboard Refactor Plan

**Date:** 2026-07-17

**Area:** Dashboard registry, loading, rendering, navigation, and data validation

**Status:** Planning only

**Security gate:** Begin only after the audit's four Medium findings are closed or explicitly accepted.

## Outcome

Make the 21 registered dashboards independently loadable, runtime-validated, and easier to extend without keeping dashboard network state in `App.svelte` or every chart-rendering branch in `InfoView.svelte`.

Resident-visible content, chart types, CSV output, navigation order, civic visual language, and accessibility must remain stable. The only intentional performance change is to stop fetching every dashboard JSON file on initial map visits.

## Current review

- `src/lib/dashboards.ts` is a good single registry for grouping, labels, descriptions, hash routing, and adjacency. Keep it.
- `src/App.svelte` loads all 21 `info-*.json` files plus summaries and freshness immediately, even when a resident only uses the map or guide. It also owns cache/error/loading state and mutates fetched panels to apply overlays.
- `src/lib/InfoView.svelte` is 445 physical lines and combines page composition, chart dispatch, accessible chart tables, CSV actions, summary/stat/table/explainer/footer rendering, and styles.
- Chart conversion, CSV helpers, headers, navigation, explainers, tables, and stat cards are already sensibly separate.
- Tests cover registry routing/adjacency, chart-to-table conversion, CSV formatting, freshness, scales, and sorting. They do not validate every real panel against a runtime schema or exercise a lazy cache/retry state machine.

## Approach decision

- **Loader plus renderer extraction — recommended.** Preserve the registry and data JSON format; create a dashboard data service and extract the cohesive chart block.
- **One Svelte component per dashboard.** Rejected: it duplicates a deliberately data-driven rendering system and makes consistency harder.
- **Generic CMS/schema rewrite.** Deferred: no evidence that an external authoring platform is needed, and it would expand security and operational scope.

## Target ownership

```text
App.svelte
  owns top-level route/shell only
  -> dashboard/dashboardData.svelte.ts
       owns metadata overlays, per-dashboard cache, loading/error/retry, optional prefetch
  -> InfoView.svelte
       composes a validated InfoPanel
       -> dashboard/DashboardChart.svelte
       -> dashboard/DashboardSummary.svelte
       -> existing StatCard, InfoTable, TaxEstimator, InfoExplainer, DashboardNav

dashboards.ts remains the only registry and ordering source.
```

## Implementation sequence

### Phase D1 — Define and validate the panel contract

**Files:** create `src/lib/dashboard/infoPanel.ts` or an equivalently focused module; add `test/infoPanel.test.ts`; review `src/lib/types.ts`.

1. Move dashboard-specific interfaces from the broad shared types file only where doing so reduces coupling; re-export types temporarily to avoid a big-bang import rewrite.
2. Add a runtime `validateInfoPanel(value, id)` boundary. Validate required title/type shapes and every optional nested array used by the renderer: summaries, stats, charts by chart type, tables, estimators, explainers, links, and freshness fields.
3. Reject unknown chart types and malformed rows with an error that names the dashboard ID and field path.
4. Test every committed `public/info-*.json` file, every registry ID, and the summary/freshness overlay maps. Fail if a registered dashboard lacks a panel file or an unregistered panel file appears accidentally.

**Exit:** The build/test suite proves that all 21 current panels satisfy the renderer's contract.

### Phase D2 — Extract a per-dashboard data service

**Files:** create `src/lib/dashboard/dashboardData.svelte.ts`; modify `src/App.svelte`; add `test/dashboardData.test.ts`.

The service owns three immutable inputs: registry IDs, `summaries.json`, and `freshness.json`. It exposes per-ID state containing `panel`, `loading`, `error`, and an explicit `load/retry` action.

Required behavior:

- fetch summary/freshness overlays once and cache their promises;
- fetch a panel only when its dashboard becomes active;
- validate before storing;
- create a new object when applying overlays instead of mutating parsed JSON;
- distinguish missing/non-OK content from network/timeout/validation errors;
- deduplicate concurrent loads and cache successful results for the session;
- retry only the requested dashboard;
- optionally prefetch the immediately adjacent dashboard after the active one settles and the browser is online;
- avoid fetching dashboard panels during a map-only or guide-only session.

Do not put route state or presentation strings into the service.

**Exit:** `App.svelte` no longer contains `panels`, `panelErrors`, `loadInfo`, or all-panel `Promise.all`. A network test proves a map-only start requests zero `info-*.json` files.

### Phase D3 — Extract the chart figure as a unit

**Files:** create `src/lib/dashboard/DashboardChart.svelte`; modify `src/lib/InfoView.svelte`; move only chart-specific styles.

The component receives one validated `InfoChart` and owns:

- chart-type dispatch to Donut, Bars, TrendLine, or CompareBars;
- figure title;
- accessible plain-data table;
- CSV export using the existing helper and the exact table values;
- chart-specific responsive styles.

Keep `chartToTable` pure and shared with Open Data. Do not introduce dynamic component machinery unless it makes exhaustiveness clearer than the current explicit switch. An exhaustive TypeScript switch is preferred so a new chart type fails at compile/test time.

**Exit:** `InfoView.svelte` contains dashboard section composition but no chart-type branches or CSV mechanics.

### Phase D4 — Extract only cohesive page sections

**Files:** create `src/lib/dashboard/DashboardSummary.svelte` and, if still justified by the post-D3 file, `DashboardFooter.svelte`; modify `InfoView.svelte`.

Move the summary callout as one resident-facing component. Move the source/freshness/links/notes/report-outdated footer only if it remains a cohesive block with several responsibilities after D3. Keep simple one-off markup in `InfoView`; do not create wrapper components solely to reach a line-count target.

Preserve the current City-specific visual hierarchy: group context, plain-language title/subtitle, “What this means for you,” key figures, evidence, source/freshness, and adjacent-dashboard navigation. Do not replace it with generic card grids or redesign the palette/type system during structural work.

**Exit:** `InfoView.svelte` reads top-to-bottom like the resident's information hierarchy and remains the page composer.

### Phase D5 — Navigation and loading-state verification

Verify the Dashboard menu as a disclosure, not an ARIA `menu`: Tab continues to work natively, arrow/Home/End remain enhancements, Escape returns focus, and outside click closes without stealing focus.

Test these route/data sequences:

- direct load of every `#<dashboard>` hash;
- Back/Forward between map, guide, and dashboards;
- first load, cached revisit, offline failure, retry success, 404/missing panel, and invalid JSON;
- rapid navigation across several dashboards without stale data appearing;
- adjacent navigation at first/middle/last positions;
- CSV and accessible data table contain identical values for every chart type;
- dark/light, narrow/desktop, print/download, and reduced-motion behavior;
- service worker update does not mix an old schema with new panel files without a clear failure state.

## Performance acceptance

Capture a browser network trace before and after:

| Scenario | Required result after refactor |
|---|---|
| Fresh load on map | No `info-*.json`; summaries/freshness may wait until first dashboard |
| First dashboard | Active panel plus shared overlays; at most one intentional adjacent prefetch |
| Revisit same dashboard | No duplicate network request in the same session |
| Offline cached dashboard | Previously cached/PWA content renders with existing offline affordance |

Do not declare a performance win from bundle size alone; record request count and transferred dashboard bytes.

## File-level deliverable

| File | Planned result |
|---|---|
| `src/App.svelte` | Top-level route/shell and map data; no dashboard cache implementation |
| `src/lib/dashboards.ts` | Retained registry and routing source |
| `src/lib/dashboard/dashboardData.svelte.ts` | Validated lazy cache, retry, metadata overlays |
| `src/lib/dashboard/infoPanel.ts` | Runtime contract and dashboard types |
| `src/lib/dashboard/DashboardChart.svelte` | Chart, accessible table, CSV unit |
| `src/lib/InfoView.svelte` | Resident-facing dashboard page composition |
| `test/infoPanel.test.ts`, `test/dashboardData.test.ts` | Real-file contract and state-machine coverage |

## Verification and rollback

Run after each phase:

```powershell
npm run check
npm test
npm run build
```

Use separate commits for contract validation, loader extraction, and renderer extraction. Lazy loading is the only approved behavior change; if it harms offline reliability or creates stale-route races, retain the extracted service but restore eager loading until those cases are solved. Do not combine this plan with map or Resident Guide edits.
