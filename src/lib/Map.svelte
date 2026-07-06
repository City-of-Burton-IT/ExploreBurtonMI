<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import 'leaflet.markercluster';
  import 'leaflet.markercluster/dist/MarkerCluster.css';
  import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
  import { Capacitor } from '@capacitor/core';
  import type { AppConfig, PlaceCollection, PlaceFeature } from './types';
  import { ui, select, openReport, setReportPin } from './store.svelte';
  import { dataFetch } from './remote';
  import { activeClosures, closuresGeoJSON, localTodayISO, type RoadClosure } from './closures';
  import { escapeHtml } from './map/html';
  import { bindClusterPreview, type PlaceMarker } from './map/clusterPreview';
  import { createGeolocation, type MapGeolocation } from './map/geolocation';
  import { addConfigOverlays } from './map/dataLayers';
  import ClosureBanner from './ClosureBanner.svelte';

  let {
    config,
    data,
    filteredIds,
  }: { config: AppConfig; data: PlaceCollection; filteredIds: Set<string> } = $props();

  let mapEl: HTMLDivElement;
  let map: L.Map | undefined;
  let cluster: L.MarkerClusterGroup | undefined;
  let layerControlEl: HTMLElement | undefined;
  // Road closures (#32): city-curated JSON, filtered to today's active set.
  let allClosures = $state<RoadClosure[]>([]);
  const activeClosureList = $derived(activeClosures(allClosures, localTodayISO()));
  let closureLayer: L.GeoJSON | undefined;
  const markers = new Map<string, L.CircleMarker>();
  // Bumped once the markers are built, so the "center on selected" effect re-runs
  // after a deep-link selection that was applied before the markers existed.
  let markerEpoch = $state(0);
  const featureById = new Map<string, PlaceFeature>();
  // "Near me" geolocation (web + native paths) — created once the map exists.
  let geo: MapGeolocation | undefined;
  let locateMsg = $state('');

  function flashLocateMsg(msg: string): void {
    locateMsg = msg;
    setTimeout(() => (locateMsg = ''), 4500);
  }

  // The native quick-actions "Near me" bumps ui.nearMeNonce; run a locate when it
  // changes (skip the initial 0 so we don't auto-locate on load).
  $effect(() => {
    if (ui.nearMeNonce > 0) geo?.locateMe();
  });

  const DEFAULT_COLOR = '#555555';

  function colorFor(feature: PlaceFeature): string {
    // A record may carry several categories (a collapsed big-box store); the first
    // is its primary, which drives the marker color.
    const raw = feature.properties[config.categoryField];
    const cat = (Array.isArray(raw) ? raw[0] : raw) as string | undefined;
    return (cat && config.categories[cat]?.color) || DEFAULT_COLOR;
  }

  function baseStyle(feature: PlaceFeature): L.CircleMarkerOptions {
    return {
      radius: 8,
      color: '#ffffff',
      weight: 1.5,
      fillColor: colorFor(feature),
      fillOpacity: 0.9,
    };
  }

  onMount(() => {
    const { center, zoom, maxZoom, minZoom, maxBounds, previewAttribute } = config.map;

    // Honor prefers-reduced-motion: turn off Leaflet's animated pan/zoom/fade.
    const reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    map = L.map(mapEl, {
      center,
      zoom,
      maxZoom,
      minZoom,
      maxBounds: L.latLngBounds(maxBounds[0], maxBounds[1]),
      // Softer than a hard lock (1.0): the map resists drifting far from Burton but
      // still lets a zoomed-in resident pan to centre on the city's edges (north,
      // etc.) without being yanked straight back. Paired with a roomier maxBounds
      // pad once the boundary loads (below).
      maxBoundsViscosity: 0.5,
      // Credits live in the About dialog instead of an on-map overlay.
      attributionControl: false,
      zoomAnimation: !reduceMotion,
      fadeAnimation: !reduceMotion,
      markerZoomAnimation: !reduceMotion,
    });

    geo = createGeolocation(map, { flash: flashLocateMsg, clear: () => (locateMsg = '') });

    L.tileLayer(config.tiles.url, {
      subdomains: config.tiles.subdomains ?? 'abc',
      maxZoom,
    }).addTo(map);

    // Transparent reference layers (labels, roads) drawn on top of the base.
    for (const overlay of config.tiles.overlays ?? []) {
      L.tileLayer(overlay.url, {
        subdomains: overlay.subdomains ?? 'abc',
        maxZoom,
      }).addTo(map);
    }

    L.control.scale({ imperial: true, metric: false }).addTo(map);

    // City-limits outline. Drawn non-interactively so it never blocks marker
    // clicks; when lockView is set, the map is pinned to the boundary's extent.
    if (config.boundary) {
      const {
        source,
        color = '#1f3a5f',
        weight = 3,
        lockView = false,
        dimOutside = false,
        dimColor = '#0b1f2e',
        dimOpacity = 0.5,
      } = config.boundary;
      dataFetch(source)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`boundary HTTP ${r.status}`))))
        .then((geojson) => {
          if (!map) return;
          const geom = geojson.type === 'Feature' ? geojson.geometry : geojson;

          // Dim everything outside the city: a world-covering polygon with the
          // boundary's exterior ring(s) punched out as holes, so only Burton stays
          // clear. Drawn first so the outline + markers sit on top.
          if (dimOutside) {
            const exteriors =
              geom?.type === 'Polygon'
                ? [geom.coordinates[0]]
                : geom?.type === 'MultiPolygon'
                  ? geom.coordinates.map((poly: number[][][]) => poly[0])
                  : [];
            if (exteriors.length) {
              const world = [
                [-179, -85],
                [179, -85],
                [179, 85],
                [-179, 85],
                [-179, -85],
              ];
              const mask = { type: 'Polygon' as const, coordinates: [world, ...exteriors] };
              L.geoJSON(mask, {
                interactive: false,
                style: { stroke: false, fillColor: dimColor, fillOpacity: dimOpacity },
              }).addTo(map);
            }
          }

          const outline = L.geoJSON(geojson, {
            interactive: false,
            style: { color, weight, fill: false, opacity: 0.9 },
          }).addTo(map);
          if (lockView) {
            const bounds = outline.getBounds();
            // Pad generously (was 0.05): at higher zoom the viewport must extend past
            // the city outline to centre on an edge (e.g. north Burton); too tight a
            // bound yanked the user's pan straight back. 0.3 gives that room while
            // still keeping the map anchored to the Burton area.
            map.setMaxBounds(bounds.pad(0.3));
            map.fitBounds(bounds);
          }
        })
        .catch((err) => console.warn('Boundary outline not loaded:', err));
    }

    // Toggleable GeoJSON + image overlays (e.g. school districts, the zoning map)
    // exposed via a layer control, OFF by default; sources load lazily on first
    // toggle. The control's container is kept so pin-drop mode can hide it.
    layerControlEl = addConfigOverlays(map, mapEl, config);

    // zoomToBoundsOnClick is off so we own the cluster tap: a small bubble shows a
    // preview of what's inside (below); a big one drills down by zooming.
    cluster = L.markerClusterGroup({ showCoverageOnHover: false, zoomToBoundsOnClick: false });
    for (const feature of data.features) {
      // Off-map entries (real location outside the city) are listed but never
      // plotted on the locked city map.
      if (feature.offMap) continue;
      const [lng, lat] = feature.geometry.coordinates;
      const label = String(feature.properties[previewAttribute] ?? feature.properties.name);
      const marker = L.circleMarker([lat, lng], baseStyle(feature));
      marker.bindTooltip(escapeHtml(label));
      marker.on('click', () => select(feature));
      (marker as PlaceMarker).feature = feature;
      markers.set(feature.id, marker);
      featureById.set(feature.id, feature);
    }
    map.addLayer(cluster);
    bindClusterPreview(map, cluster);
    markerEpoch += 1;

    // "Near me" + "Report an issue" map controls are DESKTOP-ONLY (#68 follow-up):
    // phones (mobile web + the native app) get the same actions in the quick-actions
    // row under the header instead, so the map stays uncluttered. Native never
    // creates them; mobile web hides them via the max-width rule on .near-me-btn.
    const NearMeControl = L.Control.extend({
      options: { position: 'topleft' as L.ControlPosition },
      onAdd() {
        const btn = L.DomUtil.create('button', 'near-me-btn');
        btn.type = 'button';
        btn.title = 'Center the map on my location';
        btn.setAttribute('aria-label', 'Center the map on my location');
        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '◎';
        btn.append(icon, ' Near me');
        L.DomEvent.disableClickPropagation(btn);
        L.DomEvent.on(btn, 'click', () => geo?.locateMe());
        return btn;
      },
    });
    if (!Capacitor.isNativePlatform()) map.addControl(new NearMeControl());

    // "Report an issue" (#14): opens the report form; the form sends the user
    // back here in pin mode, and the next map tap places the pin.
    const ReportControl = L.Control.extend({
      options: { position: 'topleft' as L.ControlPosition },
      onAdd() {
        const btn = L.DomUtil.create('button', 'near-me-btn');
        btn.type = 'button';
        btn.title = 'Report an issue (pothole, sign, drainage, streetlight)';
        btn.setAttribute('aria-label', 'Report an issue');
        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '⚠';
        btn.append(icon, ' Report an issue');
        L.DomEvent.disableClickPropagation(btn);
        L.DomEvent.on(btn, 'click', () => openReport());
        return btn;
      },
    });
    if (!Capacitor.isNativePlatform()) map.addControl(new ReportControl());

    map.on('click', (e: L.LeafletMouseEvent) => {
      if (ui.report.pinMode) setReportPin(e.latlng.lat, e.latlng.lng);
    });

    map.on('locationfound', (e: L.LocationEvent) => geo?.applyUserLocation(e.latlng.lat, e.latlng.lng));
    map.on('locationerror', () => {
      flashLocateMsg('Couldn’t get your location — check that location access is allowed for this site.');
    });

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
    if (!cluster) return;
    const ids = filteredIds;
    cluster.clearLayers();
    const toAdd: L.CircleMarker[] = [];
    for (const [id, marker] of markers) {
      if (ids.has(id)) toAdd.push(marker);
    }
    cluster.addLayers(toAdd);
  });

  // Road closures (#32): draw the active set as an always-on safety layer.
  // Re-runs if the JSON loads late or the active set changes; nothing renders
  // when no closure is active (the common case).
  $effect(() => {
    if (!map) return;
    const fc = closuresGeoJSON(activeClosureList);
    closureLayer?.remove();
    closureLayer = undefined;
    if (fc.features.length === 0) return;
    closureLayer = L.geoJSON(fc as GeoJSON.FeatureCollection, {
      pane: 'overlayMarkers',
      style: (f) =>
        f?.geometry.type === 'Point'
          ? {}
          : { color: String(f?.properties._color), weight: 6, opacity: 0.9 },
      pointToLayer: (f, latlng) =>
        L.circleMarker(latlng, {
          pane: 'overlayMarkers',
          radius: 9,
          color: '#ffffff',
          weight: 2,
          fillColor: String(f.properties._color),
          fillOpacity: 0.95,
        }),
      onEachFeature: (f, lyr) => {
        const p = (f.properties ?? {}) as Record<string, string>;
        const rows: [string, string][] = [];
        if (p.segment) rows.push(['Segment', p.segment]);
        if (p.reason) rows.push(['Reason', p.reason]);
        rows.push(['Dates', `${p.start} to ${p.end}`]);
        rows.push(['Closure', p.status === 'partial' ? 'Partial (lanes affected)' : 'Full']);
        if (p.detour) rows.push(['Detour', p.detour]);
        lyr.bindPopup(
          `<strong>${escapeHtml(p.road)}: closed</strong>` +
            rows.map(([k, v]) => `<div>${escapeHtml(k)}: ${escapeHtml(v)}</div>`).join(''),
        );
      },
    }).addTo(map);
  });

  // Pin-drop mode (#14): clear everything that would swallow the tap or clutter
  // the choice -- the business cluster, point overlays, hover tooltips, and the
  // layers box -- and make polygon/line overlays click-through (visible but not
  // capturing). All restored when pin mode ends.
  $effect(() => {
    if (!map) return;
    const on = ui.report.pinMode;
    if (cluster) {
      if (on) map.removeLayer(cluster);
      else if (!map.hasLayer(cluster)) map.addLayer(cluster);
    }
    for (const name of ['overlayMarkers', 'tooltipPane']) {
      const pane = map.getPane(name);
      if (pane) pane.style.display = on ? 'none' : '';
    }
    const dl = map.getPane('dataLayers');
    if (dl) dl.style.pointerEvents = on ? 'none' : '';
    if (layerControlEl) layerControlEl.style.display = on ? 'none' : '';
    if (on) map.closePopup();
  });

  // The map sits in a display:none workspace while an info view is shown, so its
  // container is 0x0 and Leaflet would otherwise reset the view on return. Capture
  // the live center/zoom BEFORE the DOM hides it ($effect.pre runs pre-DOM-update),
  // then re-measure and restore it when we come back to the map.
  let savedView: { center: L.LatLng; zoom: number } | undefined;
  $effect.pre(() => {
    if (map && ui.view !== 'map') {
      savedView = { center: map.getCenter(), zoom: map.getZoom() };
    }
  });
  $effect(() => {
    if (ui.view === 'map' && map) {
      requestAnimationFrame(() => {
        if (!map) return;
        map.invalidateSize();
        if (savedView) map.setView(savedView.center, savedView.zoom, { animate: false });
      });
    }
  });

  // Highlight the selected marker. Only restyle the two markers that change
  // (the previously- and newly-selected), not all ~1,146 every time -- the old
  // version looped every marker and did an O(n) features.find() inside, i.e. O(n^2)
  // per click.
  let prevSelectedId: string | undefined;
  $effect(() => {
    const selectedId = ui.selected?.id;
    if (selectedId === prevSelectedId) return;
    if (prevSelectedId) {
      const m = markers.get(prevSelectedId);
      const f = featureById.get(prevSelectedId);
      if (m && f) m.setStyle(baseStyle(f));
    }
    if (selectedId) {
      const m = markers.get(selectedId);
      if (m) {
        m.setStyle({ radius: 11, weight: 3, color: '#111111' });
        m.bringToFront();
      }
    }
    prevSelectedId = selectedId;
  });

  // Selecting a place (from the list or a marker) zooms in to reveal it -- using
  // markercluster's zoomToShowLayer so a marker hidden inside a cluster is
  // declustered and centred rather than left invisible. offMap features have no
  // marker and are skipped.
  $effect(() => {
    markerEpoch; // re-run after the markers are (re)built, for deep-link selections
    const id = ui.selected?.id;
    if (!id || !map || !cluster) return;
    const marker = markers.get(id);
    if (!marker) return;
    cluster.zoomToShowLayer(marker, () => marker.bringToFront());
  });

  onDestroy(() => {
    map?.remove();
    map = undefined;
    cluster = undefined;
  });
</script>

<div class="map" bind:this={mapEl} aria-label="Map of Burton"></div>
<ClosureBanner active={activeClosureList} />
{#if locateMsg}
  <div class="locate-msg" role="status" aria-live="polite">{locateMsg}</div>
{/if}
{#if ui.report.pinMode}
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
