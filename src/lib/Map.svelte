<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import 'leaflet.markercluster';
  import 'leaflet.markercluster/dist/MarkerCluster.css';
  import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
  import type { AppConfig, PlaceCollection } from './types';
  import { ui, select, setUserLocation, openReport, setReportPin } from './store.svelte';
  import { dataFetch } from './remote';
  import type { RoadClosure } from './closures';
  import { createGeolocation, type MapGeolocation } from './map/geolocation';
  import { createMapControls, type MapControlsHandle } from './map/controls';
  import { createBaseMap, type BaseMapHandle } from './map/createBaseMap';
  import { createPlaceLayer, type PlaceLayerHandle } from './map/placeLayer';
  import { createClosureLayer, type ClosureLayerHandle } from './map/closureLayer';
  import { startLocalDayRollover } from './map/closureDay';
  import {
    createReportPinModeAdapter,
    type ReportPinModeAdapter,
  } from './map/reportPinMode';
  import ClosureBanner from './ClosureBanner.svelte';

  let {
    config,
    data,
    filteredIds,
  }: { config: AppConfig; data: PlaceCollection; filteredIds: Set<string> } = $props();

  let mapEl: HTMLDivElement;
  let baseMap: BaseMapHandle | undefined;
  let placeLayer: PlaceLayerHandle | undefined;
  let map: L.Map | undefined;
  // Road closures (#32): city-curated JSON, filtered to today's active set.
  let allClosures = $state<RoadClosure[]>([]);
  let activeClosureList = $state<RoadClosure[]>([]);
  let closureLayer: ClosureLayerHandle | undefined;
  let closureDay = $state('');
  let stopClosureDayRollover: (() => void) | undefined;
  // Bumped once the markers are built, so the "center on selected" effect re-runs
  // after a deep-link selection that was applied before the markers existed.
  let markerEpoch = $state(0);
  // "Near me" geolocation (web + native paths) — created once the map exists.
  let geo: MapGeolocation | undefined;
  let mapControls: MapControlsHandle | undefined;
  let reportPinMode: ReportPinModeAdapter | undefined;
  let removeMapListeners: (() => void) | undefined;
  let locateMsg = $state('');
  let showReportPinInstructions = $state(false);
  let locateMsgTimer: ReturnType<typeof setTimeout> | undefined;

  function flashLocateMsg(msg: string): void {
    locateMsg = msg;
    if (locateMsgTimer !== undefined) clearTimeout(locateMsgTimer);
    locateMsgTimer = setTimeout(() => {
      locateMsg = '';
      locateMsgTimer = undefined;
    }, 4500);
  }

  function clearLocateMsg(): void {
    if (locateMsgTimer !== undefined) clearTimeout(locateMsgTimer);
    locateMsgTimer = undefined;
    locateMsg = '';
  }

  function synchronizeNearMe(nonce: number): void {
    if (nonce <= 0) return;
    geo?.locateMe();
  }

  function synchronizeFilteredPlaces(ids: Set<string>): void {
    const layer = placeLayer;
    if (!layer) return;
    layer.setVisible(ids);
  }

  function synchronizeClosureData(records: RoadClosure[], day: string): void {
    const layer = closureLayer;
    if (!layer || !day) return;
    activeClosureList = layer.update(records, day);
  }

  function synchronizeSelectedPlace(id: string | undefined, epoch: number): void {
    const layer = placeLayer;
    if (!layer) return;
    layer.setSelected(id ?? null);
    if (id && epoch > 0) layer.focus(id);
  }

  function synchronizeReportPinMode(enabled: boolean): void {
    const adapter = reportPinMode;
    if (!adapter) {
      showReportPinInstructions = false;
      return;
    }
    adapter.synchronize(enabled);
  }

  function captureMapView(view: string): void {
    if (view === 'map') return;
    baseMap?.captureView();
  }

  function restoreMapView(view: string): void {
    if (view !== 'map') return;
    baseMap?.restoreView();
  }

  function installMapListeners(target: L.Map): () => void {
    const handleClick = (event: L.LeafletMouseEvent) => {
      if (ui.report.pinMode) setReportPin(event.latlng.lat, event.latlng.lng);
    };
    const handleLocationFound = (event: L.LocationEvent) => {
      geo?.applyUserLocation(event.latlng.lat, event.latlng.lng);
    };
    const handleLocationError = () => {
      flashLocateMsg('Couldn’t get your location — check that location access is allowed for this site.');
    };

    target.on('click', handleClick);
    target.on('locationfound', handleLocationFound);
    target.on('locationerror', handleLocationError);
    return () => {
      target.off('click', handleClick);
      target.off('locationfound', handleLocationFound);
      target.off('locationerror', handleLocationError);
    };
  }

  // The native quick-actions "Near me" bumps ui.nearMeNonce; run a locate when it
  // changes (skip the initial 0 so we don't auto-locate on load).
  $effect(() => {
    synchronizeNearMe(ui.nearMeNonce);
  });

  onMount(() => {
    baseMap = createBaseMap(mapEl, config);
    map = baseMap.map;
    geo = createGeolocation(map, { flash: flashLocateMsg, clear: clearLocateMsg }, setUserLocation);

    // Boundary fetching remains an application concern; the base-map controller
    // only renders resolved GeoJSON and ignores it after teardown.
    if (config.boundary) {
      dataFetch(config.boundary.source)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`boundary HTTP ${r.status}`))))
        .then((geojson) => baseMap?.applyBoundary(geojson))
        .catch((err) => console.warn('Boundary outline not loaded:', err));
    }

    placeLayer = createPlaceLayer(map, data, config, select);
    closureLayer = createClosureLayer(map);
    stopClosureDayRollover = startLocalDayRollover((day) => (closureDay = day));
    activeClosureList = closureLayer.update(allClosures, closureDay);
    markerEpoch += 1;
    mapControls = createMapControls(map, {
      onLocate: () => geo?.locateMe(),
      onReport: openReport,
    });
    reportPinMode = createReportPinModeAdapter({
      map,
      mapElement: mapEl,
      getBaseMap: () => baseMap,
      getPlaceLayer: () => placeLayer,
      getClosureLayer: () => closureLayer,
      onInstructions: (visible) => (showReportPinInstructions = visible),
    });
    removeMapListeners = installMapListeners(map);
    synchronizeReportPinMode(ui.report.pinMode);

    // Road closures (#32): load the city-curated list; the $effect above draws
    // whatever is active today. A missing/invalid file just means no closures.
    dataFetch('road-closures.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((file) => {
        if (file && Array.isArray(file.closures)) allClosures = file.closures;
      })
      .catch(() => {});
  });

  // Sync which markers are on the map with the filtered set.
  $effect(() => {
    synchronizeFilteredPlaces(filteredIds);
  });

  // Reconcile the active closure layer when the fetched records change. The
  // controller returns the same active records shown in the banner.
  $effect(() => {
    synchronizeClosureData(allClosures, closureDay);
  });

  // Pin-drop mode (#14): clear everything that would swallow the tap or clutter
  // the choice -- the business cluster, point overlays, hover tooltips, and the
  // layers box -- and make polygon/line overlays click-through (visible but not
  // capturing). All restored when pin mode ends.
  $effect(() => {
    synchronizeReportPinMode(ui.report.pinMode);
  });

  // The map sits in a display:none workspace while an info view is shown, so its
  // container is 0x0 and Leaflet would otherwise reset the view on return. Capture
  // the live center/zoom BEFORE the DOM hides it ($effect.pre runs pre-DOM-update),
  // then re-measure and restore it when we come back to the map.
  $effect.pre(() => {
    captureMapView(ui.view);
  });
  $effect(() => {
    restoreMapView(ui.view);
  });

  // Synchronize selected styling and focus together. markerEpoch re-runs this
  // after the markers are built when a deep link selected a place before mount.
  $effect(() => {
    synchronizeSelectedPlace(ui.selected?.id, markerEpoch);
  });

  onDestroy(() => {
    if (locateMsgTimer !== undefined) clearTimeout(locateMsgTimer);
    locateMsgTimer = undefined;
    removeMapListeners?.();
    removeMapListeners = undefined;
    reportPinMode?.destroy();
    reportPinMode = undefined;
    mapControls?.destroy();
    mapControls = undefined;
    stopClosureDayRollover?.();
    stopClosureDayRollover = undefined;
    closureLayer?.destroy();
    closureLayer = undefined;
    placeLayer?.destroy();
    placeLayer = undefined;
    baseMap?.destroy();
    baseMap = undefined;
    geo = undefined;
    map = undefined;
  });
</script>

<div class="map" bind:this={mapEl} aria-label="Map of Burton"></div>
<ClosureBanner active={activeClosureList} />
{#if locateMsg}
  <div class="locate-msg" role="status" aria-live="polite">{locateMsg}</div>
{/if}
{#if showReportPinInstructions}
  <div class="locate-msg" role="status" aria-live="polite">
    Tap the map where the issue is
  </div>
{/if}

<style>
  .map {
    width: 100%;
    height: 100%;
  }
  /* Labeled map-action buttons ("Near me", "Report an issue") -- icon + text so
     their purpose is obvious on every platform (#68). */
  :global(.near-me-btn) {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    min-height: 34px;
    border: 2px solid rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    background: var(--pub-surface);
    color: var(--civic-blue, #2c57a0);
    font-family: var(--font-body, sans-serif);
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1;
    white-space: nowrap;
    padding: 0 0.55rem;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  }
  :global(.near-me-btn:hover) {
    background: #f4f4f4;
  }
  :global(.near-me-btn:focus-visible) {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  /* Phones get these actions in the quick-actions row instead (#68 follow-up). */
  @media (max-width: 860px) {
    :global(.near-me-btn) {
      display: none;
    }
  }
  /* Layers-box minimize toggle (#14 follow-up): explicit, works on every platform. */
  :global(.leaflet-control-layers) {
    position: relative;
  }
  :global(.layers-min-toggle) {
    position: absolute;
    top: 2px;
    right: 4px;
    border: none;
    background: none;
    padding: 0 0.3rem;
    font-size: 1.05rem;
    line-height: 1.2;
    color: var(--pub-muted, #5c5c5c);
    cursor: pointer;
  }
  :global(.layers-min-toggle:hover) {
    color: var(--civic-blue, #2c57a0);
  }
  :global(.layers-min-toggle:focus-visible) {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: 4px;
  }
  /* Minimized: the whole box shrinks to a "Layers" pill (44px touch target). */
  :global(.leaflet-control-layers.layers-minimized .leaflet-control-layers-list) {
    display: none;
  }
  :global(.leaflet-control-layers.layers-minimized) {
    min-width: 0;
  }
  :global(.leaflet-control-layers.layers-minimized .layers-min-toggle) {
    position: static;
    display: block;
    min-height: 32px;
    min-width: 44px;
    padding: 0.2rem 0.6rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--civic-blue, #2c57a0);
  }
  /* Transient location status/error toast, centered over the map. */
  .locate-msg {
    position: absolute;
    bottom: 1.25rem;
    left: 50%;
    transform: translateX(-50%);
    max-width: 90%;
    background: rgba(20, 20, 20, 0.9);
    color: #fff;
    font-size: 0.85rem;
    padding: 0.5rem 0.9rem;
    border-radius: 999px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    z-index: 1200;
    pointer-events: none;
  }

  /* Cluster preview (#map): hover tooltip + tap popup listing the places in a
     bubble. Rendered in Leaflet's own tooltip/popup containers, so :global. */
  :global(.cluster-tip .cluster-peek) {
    font-family: var(--font-body);
    max-width: 16rem;
  }
  :global(.cluster-peek .cp-head),
  :global(.cluster-preview .cp-head) {
    margin: 0 0 0.3rem;
    font-weight: 700;
    font-size: 0.82rem;
    color: var(--civic-blue-deep, #1e437e);
  }
  :global(.cluster-peek ul),
  :global(.cluster-preview ul) {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  :global(.cluster-peek li) {
    font-size: 0.82rem;
    line-height: 1.35;
  }
  :global(.cluster-peek .cp-more) {
    margin: 0.25rem 0 0;
    font-size: 0.76rem;
    color: var(--pub-muted, #5c5c5c);
  }
  /* Tap popup: a scrollable list of tappable place names. */
  :global(.cluster-preview) {
    min-width: 11rem;
  }
  :global(.cluster-preview li) {
    border-top: 1px solid var(--pub-border-soft, #f0f0f0);
  }
  :global(.cluster-preview li:first-child) {
    border-top: none;
  }
  :global(.cluster-preview li button) {
    display: block;
    width: 100%;
    text-align: left;
    border: none;
    background: none;
    padding: 0.4rem 0.2rem;
    font-family: var(--font-body);
    font-size: 0.88rem;
    color: var(--civic-blue-link, #386fc5);
    cursor: pointer;
  }
  :global(.cluster-preview li button:hover) {
    color: var(--civic-blue);
    background: var(--pub-surface-2, #f5f7fa);
  }
  :global(.cluster-preview li button:focus-visible) {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
</style>

