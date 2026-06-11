<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import 'leaflet.markercluster';
  import 'leaflet.markercluster/dist/MarkerCluster.css';
  import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
  import { Capacitor } from '@capacitor/core';
  import { Geolocation } from '@capacitor/geolocation';
  import type { AppConfig, PlaceCollection, PlaceFeature } from './types';
  import { ui, select, setUserLocation } from './store.svelte';
  import { dataFetch } from './remote';

  let {
    config,
    data,
    filteredIds,
  }: { config: AppConfig; data: PlaceCollection; filteredIds: Set<string> } = $props();

  let mapEl: HTMLDivElement;
  let map: L.Map | undefined;
  let cluster: L.MarkerClusterGroup | undefined;
  const markers = new Map<string, L.CircleMarker>();
  // Bumped once the markers are built, so the "center on selected" effect re-runs
  // after a deep-link selection that was applied before the markers existed.
  let markerEpoch = $state(0);
  const featureById = new Map<string, PlaceFeature>();
  let userMarker: L.CircleMarker | undefined;
  let locateMsg = $state('');

  function flashLocateMsg(msg: string): void {
    locateMsg = msg;
    setTimeout(() => (locateMsg = ''), 4500);
  }

  // Shared "we have the user's position" handler for both the web (Leaflet locate)
  // and native (Capacitor Geolocation) paths: sort the list nearest-first, and only
  // recenter + drop the "you are here" marker when the user is inside the city bounds.
  function applyUserLocation(lat: number, lng: number): void {
    if (!map) return;
    locateMsg = '';
    const latlng = L.latLng(lat, lng);
    setUserLocation({ lat, lng });
    // maxBounds is a LatLngBounds at construction (tightened to the city outline on
    // load), so it's a bounds instance at runtime.
    const bounds = map.options.maxBounds as L.LatLngBounds | undefined;
    if (bounds && !bounds.contains(latlng)) {
      flashLocateMsg('You appear to be outside Burton — showing the closest places on the city map.');
      return;
    }
    map.setView(latlng, Math.max(map.getZoom(), 15));
    if (!userMarker) {
      userMarker = L.circleMarker(latlng, {
        radius: 8,
        color: '#ffffff',
        weight: 3,
        fillColor: '#1976d2',
        fillOpacity: 1,
      });
      userMarker.bindTooltip('You are here');
      userMarker.addTo(map);
    } else {
      userMarker.setLatLng(latlng);
    }
    userMarker.bringToFront();
  }

  // Native (Capacitor) geolocation: request the runtime permission, then read one
  // position. Mirrors Leaflet's locationerror messaging on denial/failure.
  async function locateNative(): Promise<void> {
    try {
      const perm = await Geolocation.requestPermissions();
      if (perm.location === 'denied' && perm.coarseLocation === 'denied') {
        flashLocateMsg('Couldn’t get your location — location access is turned off for this app.');
        return;
      }
      const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true });
      applyUserLocation(pos.coords.latitude, pos.coords.longitude);
    } catch {
      flashLocateMsg('Couldn’t get your location — check that location access is allowed for this app.');
    }
  }

  const DEFAULT_COLOR = '#555555';

  // Leaflet bindTooltip/bindPopup render string content as HTML. Feature names come
  // from OpenStreetMap/Overture (community-editable), so escape them to prevent a
  // crafted name (e.g. "<img onerror=...>") from executing as DOM XSS.
  function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string,
    );
  }

  function colorFor(feature: PlaceFeature): string {
    // A record may carry several categories (a collapsed big-box store); the first
    // is its primary, which drives the marker color.
    const raw = feature.properties[config.categoryField];
    const cat = (Array.isArray(raw) ? raw[0] : raw) as string | undefined;
    return (cat && config.categories[cat]?.color) || DEFAULT_COLOR;
  }

  /** Build a CSS clip-path polygon (in element-relative %) from a boundary GeoJSON
   *  so an image overlay can be clipped to the city shape. Percentages scale with
   *  the element, so the clip tracks Leaflet's zoom/pan automatically. */
  function boundaryClipPath(
    geojson: { type: string; geometry?: { type: string; coordinates: number[][][] }; coordinates?: number[][][] },
    bounds: [[number, number], [number, number]],
  ): string {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const geom: any = (geojson as any).type === 'Feature' ? (geojson as any).geometry : geojson;
    const ring: number[][] | null =
      geom?.type === 'Polygon'
        ? geom.coordinates[0]
        : geom?.type === 'MultiPolygon'
          ? geom.coordinates[0][0]
          : null;
    if (!ring) return '';
    const [[south, west], [north, east]] = bounds;
    const pts = ring.map(([lng, lat]: number[]) => {
      const x = ((lng - west) / (east - west)) * 100;
      const y = ((north - lat) / (north - south)) * 100;
      return `${x.toFixed(2)}% ${y.toFixed(2)}%`;
    });
    return `polygon(${pts.join(', ')})`;
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
      maxBoundsViscosity: 0.8,
      // Credits live in the About dialog instead of an on-map overlay.
      attributionControl: false,
      zoomAnimation: !reduceMotion,
      fadeAnimation: !reduceMotion,
      markerZoomAnimation: !reduceMotion,
    });

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
            map.setMaxBounds(bounds.pad(0.05));
            map.fitBounds(bounds);
          }
        })
        .catch((err) => console.warn('Boundary outline not loaded:', err));
    }

    // Toggleable GeoJSON overlays (e.g. school districts) exposed via a layer
    // control, OFF by default. Drawn in a dedicated pane below the markers (so they
    // never block a marker click) and below the dim mask (so out-of-city portions
    // read as dimmed like everything else).
    if (config.dataLayers?.length || config.imageOverlays?.length) {
      map.createPane('dataLayers');
      const pane = map.getPane('dataLayers');
      if (pane) pane.style.zIndex = '350';
      // Point overlays (e.g. bridge markers) go ABOVE the business marker cluster
      // (markerPane z-600) so they stay tappable -- in the dataLayers pane (z-350)
      // a cluster sits on top and swallows the tap (most visible on the zoomed-out
      // mobile fit, where clusters blanket the map). Polygon/line overlays stay in
      // dataLayers (below the markers, so they never block a business-marker click).
      map.createPane('overlayMarkers');
      const ompane = map.getPane('overlayMarkers');
      if (ompane) ompane.style.zIndex = '650';
      const palette = ['#1565c0', '#2e7d32', '#e65100', '#6a1b9a', '#00838f', '#b3261e', '#9e9d24'];
      // Left expanded so the available overlays are always visible (the collapsed
      // toggle hid that there were layers to turn on at all).
      const layerControl = L.control
        .layers(undefined, undefined, { collapsed: false, position: 'topright' })
        .addTo(map);

      // Georeferenced image overlays (e.g. the zoning map) -- stretched to their
      // geographic bounds, semi-transparent so the basemap shows through.
      for (const ov of config.imageOverlays ?? []) {
        const img = L.imageOverlay(ov.source, ov.bounds, {
          pane: 'dataLayers',
          opacity: ov.opacity ?? 0.6,
          interactive: false,
        });

        // Clip the image to the city boundary (removes the out-of-city parts,
        // including the map sheet's baked-in legend over neighbouring areas).
        if (ov.clipToBoundary && config.boundary) {
          let clip = '';
          const applyClip = () => {
            const el = img.getElement() as HTMLElement | null;
            if (el && clip) el.style.clipPath = clip;
          };
          dataFetch(config.boundary.source)
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error('boundary'))))
            .then((gj) => {
              clip = boundaryClipPath(gj, ov.bounds);
              applyClip();
            })
            .catch((err) => console.warn('Zoning clip not applied:', err));
          img.on('add', applyClip);
        }

        // Legend image shown in a side panel while this overlay is enabled.
        if (ov.legend) {
          const panel = L.DomUtil.create('div', 'zoning-legend-panel');
          panel.style.display = 'none';
          const close = L.DomUtil.create('button', 'zlp-close', panel);
          close.type = 'button';
          close.setAttribute('aria-label', 'Hide legend');
          close.textContent = '×';
          const legendImg = L.DomUtil.create('img', '', panel) as HTMLImageElement;
          legendImg.src = ov.legend;
          legendImg.alt = 'Zoning districts color key';
          mapEl.appendChild(panel);
          L.DomEvent.disableClickPropagation(panel);
          L.DomEvent.disableScrollPropagation(panel);
          close.addEventListener('click', () => {
            panel.style.display = 'none';
          });
          img.on('add', () => {
            panel.style.display = 'block';
          });
          img.on('remove', () => {
            panel.style.display = 'none';
          });
        }

        layerControl.addOverlay(img, ov.label);
      }

      for (const layer of config.dataLayers ?? []) {
        const nameField = layer.nameField ?? 'name';
        dataFetch(layer.source)
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${layer.source} HTTP ${r.status}`))))
          .then((geojson) => {
            if (!map) return;
            // Use a feature's own color (e.g. GTFS route colors) when present;
            // otherwise assign distinct palette colors by index (e.g. districts).
            (geojson.features ?? []).forEach(
              (f: { properties: Record<string, unknown> }, i: number) => {
                f.properties._color = f.properties._color ?? palette[i % palette.length];
              },
            );
            const gj = L.geoJSON(geojson, {
              pane: 'dataLayers',
              style: (f) => {
                // Leaflet applies `style` to EVERY layer with setStyle -- including
                // the circle markers from pointToLayer -- after pointToLayer runs.
                // Returning {} for points is a no-op setStyle (merges nothing), so
                // their marker styling stays intact; polygon/line layers are unaffected.
                if (f?.geometry?.type === 'Point') return {};
                const color = (f?.properties?._color as string) ?? palette[0];
                // Per-feature style overrides (e.g. flood zones use a heavier fill so
                // the areas read as filled, not just outlined).
                const weight = (f?.properties?._weight as number) ?? 3;
                const fillOpacity = (f?.properties?._fillOpacity as number) ?? 0.12;
                // Planned/proposed lines (e.g. trails not yet built) carry a dash
                // pattern so they never read as existing; solid otherwise.
                const dashArray = (f?.properties?._dashArray as string | null) ?? undefined;
                return { color, weight, opacity: 0.9, fillColor: color, fillOpacity, dashArray };
              },
              // Point features (e.g. bridges) become colored circle markers. Leaflet
              // only calls pointToLayer for Point/MultiPoint geometry, so polygon/line
              // layers are unaffected; the `style` callback above does NOT apply to
              // these markers, so their look is set here from the feature's _color.
              pointToLayer: (feature, latlng) => {
                const color = (feature?.properties?._color as string) ?? palette[0];
                // Proportional-symbol layers (e.g. fire call volume) carry a
                // per-feature `_radius`; others keep the default dot size.
                const radius = (feature?.properties?._radius as number) ?? 7;
                return L.circleMarker(latlng, {
                  pane: 'overlayMarkers',
                  radius,
                  color: '#ffffff',
                  weight: 1.5,
                  fillColor: color,
                  fillOpacity: 0.95,
                });
              },
              onEachFeature: (feature, lyr) => {
                // Multi-field point popup: a name heading + escaped [label, value]
                // rows baked by the data tool. Each value is escaped here (the JS
                // XSS guard), so the GeoJSON never carries raw HTML.
                const rows = feature.properties?._popupRows as [string, string][] | undefined;
                if (Array.isArray(rows) && rows.length) {
                  const name = feature.properties?.[nameField];
                  const head = name ? `<strong>${escapeHtml(String(name))}</strong>` : '';
                  const body = rows
                    .map(([k, v]) => `<div>${escapeHtml(String(k))}: ${escapeHtml(String(v))}</div>`)
                    .join('');
                  lyr.bindPopup(`${head}${body}`);
                  return;
                }
                const label = feature.properties?.[nameField];
                if (!label) return;
                // Show the area name in a click/tap popup at the tap point. A popup
                // behaves identically on mouse and touch; the previous sticky
                // tooltip was positioned via mousemove, which touch devices never
                // fire, so on phones the label was unreliable/misplaced.
                lyr.bindPopup(escapeHtml(String(label)));
              },
            });
            layerControl.addOverlay(gj, layer.label);
          })
          .catch((err) => console.warn(`Data layer ${layer.source} not loaded:`, err));
      }
    }

    cluster = L.markerClusterGroup({ showCoverageOnHover: false });
    for (const feature of data.features) {
      // Off-map entries (real location outside the city) are listed but never
      // plotted on the locked city map.
      if (feature.offMap) continue;
      const [lng, lat] = feature.geometry.coordinates;
      const label = String(feature.properties[previewAttribute] ?? feature.properties.name);
      const marker = L.circleMarker([lat, lng], baseStyle(feature));
      marker.bindTooltip(escapeHtml(label));
      marker.on('click', () => select(feature));
      markers.set(feature.id, marker);
      featureById.set(feature.id, feature);
    }
    map.addLayer(cluster);
    markerEpoch += 1;

    // "Near me": a custom control that uses the browser's geolocation to center the
    // map on the user, drop a "you are here" marker, and feed ui.userLocation (which
    // sorts the list by distance). Pure client-side; degrades gracefully if denied.
    const NearMeControl = L.Control.extend({
      options: { position: 'topleft' as L.ControlPosition },
      onAdd() {
        const btn = L.DomUtil.create('button', 'near-me-btn');
        btn.type = 'button';
        btn.title = 'Center the map on my location';
        btn.setAttribute('aria-label', 'Center the map on my location');
        btn.textContent = '◎'; // ◎
        L.DomEvent.disableClickPropagation(btn);
        L.DomEvent.on(btn, 'click', () => {
          if (!map) return;
          flashLocateMsg('Locating…');
          // No setView: we recenter ourselves only when the user is inside the city
          // bounds (the map is locked to Burton, so centering on a far-away user would
          // just clamp to the edge and leave their marker unreachable off-map).
          if (Capacitor.isNativePlatform()) {
            // In the native app the WebView's navigator.geolocation needs the Android
            // runtime permission, which Leaflet's map.locate() can't request. Use the
            // Capacitor Geolocation plugin to prompt + read the position, then feed it
            // through the same handler the web path uses.
            locateNative();
          } else {
            map.locate({ enableHighAccuracy: true });
          }
        });
        return btn;
      },
    });
    map.addControl(new NearMeControl());

    map.on('locationfound', (e: L.LocationEvent) => applyUserLocation(e.latlng.lat, e.latlng.lng));
    map.on('locationerror', () => {
      flashLocateMsg('Couldn’t get your location — check that location access is allowed for this site.');
    });
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
{#if locateMsg}
  <div class="locate-msg" role="status" aria-live="polite">{locateMsg}</div>
{/if}

<style>
  .map {
    width: 100%;
    height: 100%;
  }
  /* "Near me" control button -- matches Leaflet's own control look. */
  :global(.near-me-btn) {
    width: 34px;
    height: 34px;
    border: 2px solid rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    background: #fff;
    color: var(--civic-blue, #2c57a0);
    font-size: 1.2rem;
    line-height: 1;
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
</style>
