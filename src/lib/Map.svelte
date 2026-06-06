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
    if (config.dataLayers?.length || config.imageOverlays?.length) {
      map.createPane('dataLayers');
      const pane = map.getPane('dataLayers');
      if (pane) pane.style.zIndex = '350';
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
          fetch(config.boundary.source)
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
        fetch(layer.source)
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
                const color = (f?.properties?._color as string) ?? palette[0];
                // Per-feature style overrides (e.g. flood zones use a heavier fill so
                // the areas read as filled, not just outlined).
                const weight = (f?.properties?._weight as number) ?? 3;
                const fillOpacity = (f?.properties?._fillOpacity as number) ?? 0.12;
                return { color, weight, opacity: 0.9, fillColor: color, fillOpacity };
              },
              onEachFeature: (feature, lyr) => {
                const label = feature.properties?.[nameField];
                if (!label) return;
                // Show the area name in a click/tap popup at the tap point. A popup
                // behaves identically on mouse and touch; the previous sticky
                // tooltip was positioned via mousemove, which touch devices never
                // fire, so on phones the label was unreliable/misplaced.
                lyr.bindPopup(String(label));
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

  // Selecting a place (from the list or a marker) zooms in to reveal it -- using
  // markercluster's zoomToShowLayer so a marker hidden inside a cluster is
  // declustered and centred rather than left invisible. offMap features have no
  // marker and are skipped.
  $effect(() => {
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

<style>
  .map {
    width: 100%;
    height: 100%;
  }
</style>
