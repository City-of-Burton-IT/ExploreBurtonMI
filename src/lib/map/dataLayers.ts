// Toggleable overlays from config: GeoJSON data layers (e.g. school districts,
// bridges) and georeferenced image overlays (e.g. the zoning map), exposed via a
// Leaflet layer control, OFF by default. GeoJSON sources are fetched lazily on the
// first toggle-on (not at mount), so the ~dozen overlay files (~670 KB) cost
// nothing until a user actually opens one.
import L from 'leaflet';
import type { AppConfig, DataLayerConfig, ImageOverlayConfig } from '../types';
import { dataFetch } from '../remote';
import { escapeHtml } from './html';
import { boundaryClipPath } from './clip';

const palette = ['#1565c0', '#2e7d32', '#e65100', '#6a1b9a', '#00838f', '#b3261e', '#9e9d24'];

/** Add the config-driven overlay layers + their layer control to the map.
 *  Returns the layer control's container element (the map component hides it in
 *  pin-drop mode), or undefined when the config defines no overlays. */
export function addConfigOverlays(
  map: L.Map,
  mapEl: HTMLElement,
  config: AppConfig,
): HTMLElement | undefined {
  if (!config.dataLayers?.length && !config.imageOverlays?.length) return undefined;

  // Drawn in a dedicated pane below the markers (so they never block a marker
  // click) and below the dim mask (so out-of-city portions read as dimmed like
  // everything else).
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
  // Left expanded so the available overlays are always visible (the collapsed
  // toggle hid that there were layers to turn on at all) -- but with an explicit
  // minimize toggle (below) so the box can get out of the way on any platform.
  const layerControl = L.control
    .layers(undefined, undefined, { collapsed: false, position: 'topright' })
    .addTo(map);

  bindMinimizeToggle(layerControl);

  for (const ov of config.imageOverlays ?? []) {
    layerControl.addOverlay(buildImageOverlay(map, mapEl, config, ov), ov.label);
  }
  for (const layer of config.dataLayers ?? []) {
    layerControl.addOverlay(buildDataLayer(layer), layer.label);
  }

  return layerControl.getContainer();
}

// Minimize/restore toggle for the layers box. Unlike Leaflet's collapsed
// mode (hover/tap driven), this is an explicit click toggle that works the
// same in desktop browsers, mobile web, and the Android app. State persists
// per device.
function bindMinimizeToggle(layerControl: L.Control.Layers): void {
  const lc = layerControl.getContainer();
  if (!lc) return;
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

// Georeferenced image overlay (e.g. the zoning map) -- stretched to its
// geographic bounds, semi-transparent so the basemap shows through. The image
// itself only loads when the overlay is toggled on (Leaflet creates the <img>
// on add); the boundary-clip fetch is likewise deferred to the first add.
function buildImageOverlay(
  map: L.Map,
  mapEl: HTMLElement,
  config: AppConfig,
  ov: ImageOverlayConfig,
): L.ImageOverlay {
  const img = L.imageOverlay(ov.source, ov.bounds, {
    pane: 'dataLayers',
    opacity: ov.opacity ?? 0.6,
    interactive: false,
  });

  // Clip the image to the city boundary (removes the out-of-city parts,
  // including the map sheet's baked-in legend over neighbouring areas).
  if (ov.clipToBoundary && config.boundary) {
    const boundarySource = config.boundary.source;
    let clip = '';
    let requested = false;
    const applyClip = () => {
      const el = img.getElement() as HTMLElement | null;
      if (el && clip) el.style.clipPath = clip;
    };
    img.on('add', () => {
      if (clip) {
        applyClip();
        return;
      }
      if (requested) return;
      requested = true;
      dataFetch(boundarySource)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('boundary'))))
        .then((gj) => {
          clip = boundaryClipPath(gj, ov.bounds);
          applyClip();
        })
        .catch((err) => console.warn('Zoning clip not applied:', err));
    });
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

  return img;
}

// A toggleable GeoJSON overlay, wrapped in a layer group so it can sit in the
// layer control before its data exists: the source is fetched on the first
// toggle-on and the built layer dropped into the group. A failed fetch resets
// the guard so the next toggle retries.
function buildDataLayer(layer: DataLayerConfig): L.LayerGroup {
  const nameField = layer.nameField ?? 'name';
  const group = L.layerGroup();
  let requested = false;
  group.on('add', () => {
    if (requested) return;
    requested = true;
    dataFetch(layer.source)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${layer.source} HTTP ${r.status}`))))
      .then((geojson) => {
        group.addLayer(buildGeoJsonLayer(geojson, nameField));
      })
      .catch((err) => {
        requested = false;
        console.warn(`Data layer ${layer.source} not loaded:`, err);
      });
  });
  return group;
}

function buildGeoJsonLayer(
  geojson: { features?: { properties: Record<string, unknown> }[] },
  nameField: string,
): L.GeoJSON {
  // Use a feature's own color (e.g. GTFS route colors) when present;
  // otherwise assign distinct palette colors by index (e.g. districts).
  (geojson.features ?? []).forEach((f: { properties: Record<string, unknown> }, i: number) => {
    f.properties._color = f.properties._color ?? palette[i % palette.length];
  });
  return L.geoJSON(geojson as GeoJSON.GeoJSON, {
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
}
