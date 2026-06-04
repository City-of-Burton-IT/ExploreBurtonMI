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

    cluster = L.markerClusterGroup({ showCoverageOnHover: false });
    for (const feature of data.features) {
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
