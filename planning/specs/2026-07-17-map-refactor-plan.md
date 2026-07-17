# Map Refactor Plan

**Date:** 2026-07-17

**Area:** Interactive Leaflet map

**Status:** Planning only

**Security gate:** Do not start until SEC-01 through SEC-04 in the comprehensive audit are closed or explicitly accepted.

## Outcome

Turn `src/lib/Map.svelte` into a readable Svelte/Leaflet orchestrator while preserving every resident-visible behavior: clustering, filters, selection/deep links, boundary masking, configured overlays, road closures, saved places, location, report-pin mode, responsive behavior, and native app behavior.

The goal is not a smaller file by itself. The goal is explicit ownership and testable transitions at the Leaflet/Svelte boundary.

## Current review

`Map.svelte` is 564 physical lines and has already improved since the older refactoring plan: cluster previews, geolocation, configured data layers, and HTML escaping are separate modules. The remaining component still owns four distinct responsibilities:

1. Leaflet map creation, tile/base/reference layers, City boundary and dim mask.
2. Place marker creation, cluster membership, filter reconciliation, styling, popup/tooltip behavior, and selected-place synchronization.
3. Road-closure loading/layer replacement and banner state.
4. Controls and interaction modes: locate, report-pin, map taps, view restoration, and teardown.

Current pure tests cover boundary clipping, HTML escaping, cluster summaries, and closure transforms. They do not cover marker reconciliation, selected-marker style transitions, or controller teardown.

## Approach decision

Three approaches were considered:

- **Incremental controller extraction — recommended.** Keep `Map.svelte`, Leaflet, the store, and current data contracts. Extract two stateful Leaflet controllers and one control installer behind narrow interfaces.
- **Feature-folder rewrite.** Move all map files and types at once. This improves naming but creates broad import churn without improving behavior.
- **Map framework replacement.** Replace Leaflet/Svelte integration. This is unjustified risk for a stable public map and is rejected.

## Target ownership

```text
Map.svelte
  owns Svelte lifecycle, reactive effects, resident-visible state, and orchestration
  -> map/createBaseMap.ts
       owns Leaflet instance, tiles, boundary/mask, configured static overlays
  -> map/placeLayer.ts
       owns place markers, cluster, filtering, selection, popup/tooltip events
  -> map/closureLayer.ts
       owns closure fetch-to-layer reconciliation and active closure projection
  -> map/controls.ts
       installs/removes Locate and Report controls; emits typed callbacks
  -> map/geolocation.ts, dataLayers.ts, clusterPreview.ts, html.ts
       remain focused existing modules
```

Do not move application routing, `ui` state, or report-modal state into Leaflet controllers. Controllers receive values and emit callbacks; `Map.svelte` remains the adapter to Svelte state.

## Implementation sequence

### Phase M1 — Freeze behavior with contract tests

**Files:** existing `test/mapClip.test.ts`, `test/cluster.test.ts`, `test/closures.test.ts`; new focused tests under `test/`.

1. Add fixtures representing a government place, a business, an unknown/missing category, selected and unselected markers, and a filtered-out marker.
2. Add pure tests for category color/style selection and popup/tooltip presentation.
3. Add controller tests with a small Leaflet test double for:
   - first render creates one marker per feature;
   - a filter update changes cluster membership without duplicating markers;
   - selection changes reset the old marker and emphasize/open the new marker;
   - clearing selection restores base styles;
   - destroy removes listeners and layers.
4. Preserve existing tests unchanged as regression evidence.

**Exit:** Tests describe current behavior before production extraction begins.

### Phase M2 — Extract base-map construction

**Files:** create `src/lib/map/createBaseMap.ts`; modify `src/lib/Map.svelte`; retain `src/lib/map/dataLayers.ts`.

Create a single factory that accepts the host element and `AppConfig`, then returns a handle containing the Leaflet map, initialized reference layers, and a `destroy()` method. Move only stable imperative setup:

- map options and initial view;
- aerial/base tile layers and attributions;
- City boundary and outside-boundary mask;
- configured overlay registration;
- resize/view restoration hooks that are purely Leaflet concerns.

Keep data fetching and Svelte/store reads out of the factory. Make teardown idempotent.

**Exit:** `Map.svelte` creates and destroys a base-map handle; map initialization output and visible layers are unchanged.

### Phase M3 — Extract the place-layer controller

**Files:** create `src/lib/map/placeLayer.ts`; modify `src/lib/Map.svelte`; extend map tests.

Move marker/cluster ownership as one cohesive unit:

- build each `L.CircleMarker` exactly once per place ID;
- bind escaped tooltip/popup content and cluster preview;
- reconcile visible IDs against cluster membership;
- apply selected/unselected styles;
- reveal and open the selected marker when requested;
- emit `onSelect(feature)` rather than importing the global store;
- expose `setVisible(ids)`, `setSelected(id | null)`, `focus(id)`, and `destroy()`.

Keep `PlaceFeature` as the public domain type. Do not expose marker maps to `Map.svelte` or mutate feature objects.

**Exit:** Marker creation, filtering, clustering, and selection are absent from `Map.svelte`; contract tests and existing filter/deep-link tests pass.

### Phase M4 — Isolate closure-layer reconciliation

**Files:** create `src/lib/map/closureLayer.ts`; modify `src/lib/Map.svelte`; retain `src/lib/closures.ts` pure transforms.

The controller should accept already-fetched closure records, calculate the active set through existing pure helpers, replace its GeoJSON layer only when the signature changes, and return the active records used by `ClosureBanner`. It must escape all popup fields and own layer teardown.

Fetching remains in the orchestrator or a shared remote loader so network error/retry policy does not become a Leaflet concern.

**Exit:** A closure update cannot leak a stale layer or duplicate features; banner and map derive from the same active set.

### Phase M5 — Extract custom controls and simplify effects

**Files:** create `src/lib/map/controls.ts`; modify `src/lib/Map.svelte`; add focused tests.

Install Locate and Report controls through a typed callback object. The returned handle removes DOM listeners and Leaflet controls. Preserve 48-pixel touch targets, accessible labels, keyboard activation, transient location messages, and pin-mode instructions.

Then consolidate `Map.svelte` effects into named adapter functions:

- filtered IDs -> `placeLayer.setVisible`;
- selected place -> `placeLayer.setSelected/focus`;
- near-me nonce -> existing geolocation controller;
- report pin mode -> cursor/instruction state;
- closure data -> `closureLayer.update`.

**Exit:** `Map.svelte` reads as lifecycle plus five explicit state synchronizations. No controller imports the application store.

### Phase M6 — Responsive, accessibility, and native verification

Test at narrow phone, tablet breakpoint, and desktop widths, in light/dark themes and with reduced motion. Verify:

- keyboard focus can reach and activate map controls;
- map controls have visible focus and useful accessible names;
- selecting from the list focuses the correct marker and Back/Forward restores state;
- cluster previews contain escaped resident data and correct overflow counts;
- saved-only/filter/search changes never leave duplicate or stale markers;
- location denial, timeout, and offline states remain understandable;
- report-pin mode exits on submit, cancel, and modal close;
- boundary/mask and configured overlays match the pre-refactor screenshots;
- Android hardware Back, app links, safe areas, and widget navigation remain unchanged.

## File-level deliverable

| File | Planned result |
|---|---|
| `src/lib/Map.svelte` | Orchestrator only; roughly 250–320 lines including styles, without artificial fragmentation |
| `src/lib/map/createBaseMap.ts` | Base Leaflet instance and static/reference layer lifecycle |
| `src/lib/map/placeLayer.ts` | Marker/cluster/filter/selection controller |
| `src/lib/map/closureLayer.ts` | Closure GeoJSON lifecycle |
| `src/lib/map/controls.ts` | Locate/report control lifecycle |
| `test/map*.test.ts` | Contract tests for controllers and presentation |

## Acceptance and rollback

Run after every phase:

```powershell
npm run check
npm test
npm run build
```

Commit each phase separately. If a phase changes screenshots, marker counts, route behavior, or native behavior without an approved requirement, revert that phase rather than compensating in a later extraction. Do not combine this work with dashboard or Resident Guide changes.
