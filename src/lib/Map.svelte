<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import 'leaflet.markercluster';
  import 'leaflet.markercluster/dist/MarkerCluster.css';
  import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
  import type { AppConfig, PlaceCollection, PlaceFeature } from './types';
  import { ui, select } from './store.svelte';

  let {
    config,
    data,
    filteredIds,
  }: { config: AppConfig; data: PlaceCollection; filteredIds: Set<string> } = $props();

  let mapEl: HTMLDivElement;
  let map: L.Map | undefined;
  let cluster: L.MarkerClusterGroup | undefined;
  const markers = new Map<string, L.CircleMarker>();

  const DEFAULT_COLOR = '#555555';

  function colorFor(feature: PlaceFeature): string {
    const cat = feature.properties[config.categoryField] as string | undefined;
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

    map = L.map(mapEl, {
      center,
      zoom,
      maxZoom,
      minZoom,
      maxBounds: L.latLngBounds(maxBounds[0], maxBounds[1]),
      maxBoundsViscosity: 0.8,
      // Credits live in the About dialog instead of an on-map overlay.
      attributionControl: false,
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
      fetch(source)
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
    if (config.dataLayers?.length) {
      map.createPane('dataLayers');
      const pane = map.getPane('dataLayers');
      if (pane) pane.style.zIndex = '350';
      const palette = ['#1565c0', '#2e7d32', '#e65100', '#6a1b9a', '#00838f', '#b3261e', '#9e9d24'];
      const layerControl = L.control
        .layers(undefined, undefined, { collapsed: true, position: 'topright' })
        .addTo(map);
      for (const layer of config.dataLayers) {
        const nameField = layer.nameField ?? 'name';
        fetch(layer.source)
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${layer.source} HTTP ${r.status}`))))
          .then((geojson) => {
            if (!map) return;
            (geojson.features ?? []).forEach(
              (f: { properties: Record<string, unknown> }, i: number) => {
                f.properties._color = palette[i % palette.length];
              },
            );
            const gj = L.geoJSON(geojson, {
              pane: 'dataLayers',
              style: (f) => {
                const color = (f?.properties?._color as string) ?? palette[0];
                return { color, weight: 2, opacity: 0.9, fillColor: color, fillOpacity: 0.12 };
              },
              onEachFeature: (feature, lyr) => {
                const label = feature.properties?.[nameField];
                if (label) lyr.bindTooltip(String(label), { sticky: true });
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
      marker.bindTooltip(label);
      marker.on('click', () => select(feature));
      markers.set(feature.id, marker);
    }
    map.addLayer(cluster);
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

  // Highlight the selected marker; reset the rest.
  $effect(() => {
    const selectedId = ui.selected?.id;
    for (const [id, marker] of markers) {
      const feature = data.features.find((f) => f.id === id)!;
      if (id === selectedId) {
        marker.setStyle({ radius: 11, weight: 3, color: '#111111' });
        marker.bringToFront();
      } else {
        marker.setStyle(baseStyle(feature));
      }
    }
  });

  onDestroy(() => {
    map?.remove();
    map = undefined;
    cluster = undefined;
  });
</script>

<div class="map" bind:this={mapEl} aria-label="Map of Burton"></div>

<style>
  .map {
    width: 100%;
    height: 100%;
  }
</style>
