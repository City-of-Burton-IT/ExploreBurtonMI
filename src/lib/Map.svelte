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
  import { ui, select, setUserLocation, openReport, setReportPin } from './store.svelte';
  import { dataFetch } from './remote';
  import { clusterSummary, CLUSTER_PREVIEW_MAX } from './cluster';
  import { activeClosures, closuresGeoJSON, localTodayISO, type RoadClosure } from './closures';
  import ClosureBanner from './ClosureBanner.svelte';

  /** A map layer (our circle markers) carrying its source place feature, so a
   *  cluster preview can read the names inside. Typed as the common Layer base so
   *  it fits both the circleMarkers we create and getAllChildMarkers()'s Marker[]. */
  type PlaceMarker = L.Layer & { feature?: PlaceFeature };

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

  // "Near me": locate the user via the right path for the platform. Shared by the
  // map's own control button and the native quick-actions row (via ui.nearMeNonce).
  function locateMe(): void {
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
  }

  // The native quick-actions "Near me" bumps ui.nearMeNonce; run a locate when it
  // changes (skip the initial 0 so we don't auto-locate on load).
  $effect(() => {
    if (ui.nearMeNonce > 0) locateMe();
  });

  const DEFAULT_COLOR = '#555555';

  // Leaflet bindTooltip/bindPopup render string content as HTML. Feature names come
  // from OpenStreetMap/Overture (community-editable), so escape them to prevent a
  // crafted name (e.g. "<img onerror=...>") from executing as DOM XSS.
  function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string,
    );
  }

  // --- Cluster preview (#map): peek at the places inside a cluster bubble --------
  // markercluster's cluster events carry the hovered/clicked cluster on `.layer`.
  type ClusterEvent = L.LeafletEvent & { layer: L.MarkerCluster };

  function clusterNames(c: L.MarkerCluster): string[] {
    return (c.getAllChildMarkers() as PlaceMarker[])
      .map((m) => m.feature?.properties?.name)
      .filter((n): n is string => typeof n === 'string');
  }

  function bindClusterPreview(group: L.MarkerClusterGroup): void {
    // Desktop hover: a quick tooltip with a few names + "+N more".
    group.on('clustermouseover', (e) => {
      const c = (e as ClusterEvent).layer;
      const { shown, more } = clusterSummary(clusterNames(c), 6);
      const list = shown.map((n) => `<li>${escapeHtml(n)}</li>`).join('');
      const extra = more ? `<p class="cp-more">+${more} more — tap to see</p>` : '';
      c.bindTooltip(
        `<div class="cluster-peek"><p class="cp-head">${c.getChildCount()} places here</p><ul>${list}</ul>${extra}</div>`,
        { direction: 'top', offset: [0, -6], className: 'cluster-tip' },
      ).openTooltip();
    });
    group.on('clustermouseout', (e) => (e as ClusterEvent).layer.closeTooltip());

    // Tap / click: a small bubble opens a popup listing its places (tap one to open
    // it); a big bubble zooms to drill in (the hover tooltip covers the glance there,
    // and a 100-name popup wouldn't be useful).
    group.on('clusterclick', (e) => {
      if (!map) return;
      const c = (e as ClusterEvent).layer;
      if (c.getChildCount() > CLUSTER_PREVIEW_MAX) {
        map.fitBounds(c.getBounds(), { padding: [40, 40] });
      } else {
        openClusterPreview(c);
      }
    });
  }

  function openClusterPreview(c: L.MarkerCluster): void {
    const feats = (c.getAllChildMarkers() as PlaceMarker[])
      .map((m) => m.feature)
      .filter((f): f is PlaceFeature => !!f)
      .sort((a, b) => String(a.properties.name).localeCompare(String(b.properties.name)));
    const el = L.DomUtil.create('div', 'cluster-preview');
    const head = L.DomUtil.create('p', 'cp-head', el);
    head.textContent = `${feats.length} places here`;
    const ul = L.DomUtil.create('ul', '', el);
    for (const f of feats) {
      const li = L.DomUtil.create('li', '', ul);
      const btn = L.DomUtil.create('button', '', li) as HTMLButtonElement;
      btn.type = 'button';
      btn.textContent = String(f.properties.name); // textContent => no XSS
      L.DomEvent.on(btn, 'click', (ev) => {
        L.DomEvent.stop(ev);
        map?.closePopup();
        select(f); // opens the detail sheet + reveals it on the map
      });
    }
    c.bindPopup(el, { className: 'cluster-popup', maxHeight: 260 }).openPopup();
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
      // toggle hid that there were layers to turn on at all) -- but with an explicit
      // minimize toggle (below) so the box can get out of the way on any platform.
      const layerControl = L.control
        .layers(undefined, undefined, { collapsed: false, position: 'topright' })
        .addTo(map);

      // Minimize/restore toggle for the layers box. Unlike Leaflet's collapsed
      // mode (hover/tap driven), this is an explicit click toggle that works the
      // same in desktop browsers, mobile web, and the Android app. State persists
      // per device.
      layerControlEl = layerControl.getContainer();
      if (layerControlEl) {
        const lc = layerControlEl;
        const toggle = L.DomUtil.create('button', 'layers-min-toggle', lc);
        toggle.type = 'button';
        const setMin = (min: boolean) => {
          lc.classList.toggle('layers-minimized', min);
          toggle.textContent = min ? 'Layers' : '–';
          toggle.title = min ? 'Show map layers' : 'Minimize the layers box';
          toggle.setAttribute('aria-label', toggle.title);
          toggle.setAttribute('aria-expanded', String(!min));
        };
        L.DomEvent.disableClickPropagation(toggle);
        L.DomEvent.on(toggle, 'click', () => {
          const min = !lc.classList.contains('layers-minimized');
          setMin(min);
          try {
            localStorage.setItem('eb-layers-min', min ? '1' : '0');
          } catch {
            /* private mode -- session-only */
          }
        });
        let initialMin = false;
        try {
          initialMin = localStorage.getItem('eb-layers-min') === '1';
        } catch {
          /* ignore */
        }
        setMin(initialMin);
      }

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
    bindClusterPreview(cluster);
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
        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '◎';
        btn.append(icon, ' Near me');
        L.DomEvent.disableClickPropagation(btn);
        L.DomEvent.on(btn, 'click', () => locateMe());
        return btn;
      },
    });
    map.addControl(new NearMeControl());

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
    map.addControl(new ReportControl());

    map.on('click', (e: L.LeafletMouseEvent) => {
      if (ui.report.pinMode) setReportPin(e.latlng.lat, e.latlng.lng);
    });

    map.on('locationfound', (e: L.LocationEvent) => applyUserLocation(e.latlng.lat, e.latlng.lng));
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
          `<strong>${escapeHtml(p.road)} -- closed</strong>` +
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
  /* Edge-to-edge (#30): lift Leaflet's bottom controls (attribution, any future
     bottom-anchored control) above the gesture/nav bar. 0 on the web. */
  .map :global(.leaflet-bottom) {
    margin-bottom: var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0px));
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
  /* Transient location status/error toast, centered over the map. Lifted clear
     of the gesture/nav bar on edge-to-edge devices (#30). */
  .locate-msg {
    position: absolute;
    bottom: calc(1.25rem + var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0px)));
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
