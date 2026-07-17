import L from 'leaflet';
import type { AppConfig } from '../types';
import { addConfigOverlays, type ConfigOverlays } from './dataLayers';

export interface BaseMapHandle {
  readonly map: L.Map;
  applyBoundary(geojson: GeoJSON.GeoJsonObject): void;
  captureView(): void;
  restoreView(): void;
  setOverlaySuppressed(suppressed: boolean): void;
  destroy(): void;
}

interface SavedView {
  center: L.LatLng;
  zoom: number;
}

export function createBaseMap(host: HTMLElement, config: AppConfig): BaseMapHandle {
  const { center, zoom, maxZoom, minZoom, maxBounds } = config.map;
  const reduceMotion =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  const map = L.map(host, {
    center,
    zoom,
    maxZoom,
    minZoom,
    maxBounds: L.latLngBounds(maxBounds[0], maxBounds[1]),
    maxBoundsViscosity: 0.5,
    attributionControl: false,
    zoomAnimation: !reduceMotion,
    fadeAnimation: !reduceMotion,
    markerZoomAnimation: !reduceMotion,
  });

  L.tileLayer(config.tiles.url, {
    subdomains: config.tiles.subdomains ?? 'abc',
    maxZoom,
  }).addTo(map);

  for (const overlay of config.tiles.overlays ?? []) {
    L.tileLayer(overlay.url, {
      subdomains: overlay.subdomains ?? 'abc',
      maxZoom,
    }).addTo(map);
  }

  L.control.scale({ imperial: true, metric: false }).addTo(map);

  const configuredOverlays: ConfigOverlays | undefined = addConfigOverlays(map, host, config);
  let savedView: SavedView | undefined;
  let restoreFrame: number | undefined;
  let destroyed = false;

  return {
    map,
    applyBoundary(geojson) {
      if (destroyed || !config.boundary) return;
      const {
        color = '#1f3a5f',
        weight = 3,
        lockView = false,
        dimOutside = false,
        dimColor = '#0b1f2e',
        dimOpacity = 0.5,
      } = config.boundary;
      const geom =
        geojson.type === 'Feature' ? (geojson as GeoJSON.Feature).geometry : geojson;

      if (dimOutside) {
        const exteriors =
          geom?.type === 'Polygon'
            ? [(geom as GeoJSON.Polygon).coordinates[0]]
            : geom?.type === 'MultiPolygon'
              ? (geom as GeoJSON.MultiPolygon).coordinates.map((polygon) => polygon[0])
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
        map.setMaxBounds(bounds.pad(0.3));
        map.fitBounds(bounds);
      }
    },
    captureView() {
      if (destroyed) return;
      savedView = { center: map.getCenter(), zoom: map.getZoom() };
    },
    restoreView() {
      if (destroyed) return;
      if (restoreFrame !== undefined) cancelAnimationFrame(restoreFrame);
      restoreFrame = requestAnimationFrame(() => {
        restoreFrame = undefined;
        if (destroyed) return;
        map.invalidateSize();
        if (savedView) map.setView(savedView.center, savedView.zoom, { animate: false });
      });
    },
    setOverlaySuppressed(suppressed) {
      if (destroyed) return;
      for (const name of ['overlayMarkers', 'tooltipPane']) {
        const pane = map.getPane(name);
        if (pane) pane.style.display = suppressed ? 'none' : '';
      }
      const dataLayersPane = map.getPane('dataLayers');
      if (dataLayersPane) dataLayersPane.style.pointerEvents = suppressed ? 'none' : '';
      if (configuredOverlays?.container) {
        configuredOverlays.container.style.display = suppressed ? 'none' : '';
      }
      if (suppressed) map.closePopup();
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      if (restoreFrame !== undefined) {
        cancelAnimationFrame(restoreFrame);
        restoreFrame = undefined;
      }
      configuredOverlays?.destroy();
      map.remove();
      savedView = undefined;
    },
  };
}

