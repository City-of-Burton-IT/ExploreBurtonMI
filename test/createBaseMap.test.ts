import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AppConfig } from '../src/lib/types';
import { createLeafletTestDouble, createTestElement } from './helpers/leaflet';

const leaflet = createLeafletTestDouble();
vi.doMock('leaflet', () => ({ default: leaflet }));

const { createBaseMap } = await import('../src/lib/map/createBaseMap');

function config(overrides: Partial<AppConfig> = {}): AppConfig {
  return {
    map: {
      center: [43.002, -83.632],
      zoom: 12,
      maxZoom: 19,
      minZoom: 10,
      maxBounds: [
        [42.8, -83.9],
        [43.2, -83.4],
      ],
      previewAttribute: 'name',
    },
    tiles: {
      url: 'https://tiles.example.test/{s}/{z}/{x}/{y}',
      attribution: 'Test tiles',
      overlays: [{ url: 'https://labels.example.test/{s}/{z}/{x}/{y}' }],
    },
    ...overrides,
  } as AppConfig;
}

const boundary = {
  type: 'Feature',
  properties: {},
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [-83.7, 42.9],
        [-83.5, 42.9],
        [-83.5, 43.1],
        [-83.7, 42.9],
      ],
    ],
  },
} as GeoJSON.Feature<GeoJSON.Polygon>;

let animationFrames: FrameRequestCallback[];

beforeEach(() => {
  animationFrames = [];
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    animationFrames.push(callback);
    return animationFrames.length;
  });
  vi.stubGlobal('cancelAnimationFrame', vi.fn());
  vi.stubGlobal('window', {
    matchMedia: () => ({ matches: true }),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('createBaseMap', () => {
  it('preserves map, tile, scale, and reduced-motion options', () => {
    const host = createTestElement();
    const handle = createBaseMap(host as unknown as HTMLElement, config());
    const map = leaflet.maps.at(-1)!;

    expect(map.options).toMatchObject({
      center: [43.002, -83.632],
      zoom: 12,
      maxZoom: 19,
      minZoom: 10,
      maxBoundsViscosity: 0.5,
      attributionControl: false,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
    });
    expect(map.options.maxBounds).toMatchObject({
      points: [
        [42.8, -83.9],
        [43.2, -83.4],
      ],
    });
    expect(leaflet.tileLayers.slice(-2).map((layer) => [layer.source, layer.options])).toEqual([
      ['https://tiles.example.test/{s}/{z}/{x}/{y}', { subdomains: 'abc', maxZoom: 19 }],
      ['https://labels.example.test/{s}/{z}/{x}/{y}', { subdomains: 'abc', maxZoom: 19 }],
    ]);
    expect(leaflet.scaleControls.at(-1)?.options).toEqual({ imperial: true, metric: false });

    handle.destroy();
  });

  it('applies the configured world mask, outline, and padded locked bounds', () => {
    const handle = createBaseMap(
      createTestElement() as unknown as HTMLElement,
      config({
        boundary: {
          source: 'boundary.geojson',
          lockView: true,
          dimOutside: true,
        },
      }),
    );
    const map = leaflet.maps.at(-1)!;
    const firstLayer = leaflet.geoJsonLayers.length;

    handle.applyBoundary(boundary);

    const [mask, outline] = leaflet.geoJsonLayers.slice(firstLayer);
    expect(mask.source).toEqual({
      type: 'Polygon',
      coordinates: [
        [
          [-179, -85],
          [179, -85],
          [179, 85],
          [-179, 85],
          [-179, -85],
        ],
        boundary.geometry.coordinates[0],
      ],
    });
    expect(mask.options).toEqual({
      interactive: false,
      style: { stroke: false, fillColor: '#0b1f2e', fillOpacity: 0.5 },
    });
    expect(outline.source).toBe(boundary);
    expect(outline.options).toEqual({
      interactive: false,
      style: { color: '#1f3a5f', weight: 3, fill: false, opacity: 0.9 },
    });
    expect(map.setMaxBoundsCalls).toEqual([{ ...outline.bounds, padFactor: 0.3 }]);
    expect(map.fitBoundsCalls).toEqual([outline.bounds]);

    handle.destroy();
  });

  it('captures and asynchronously restores the visible map view', () => {
    const handle = createBaseMap(createTestElement() as unknown as HTMLElement, config());
    const map = leaflet.maps.at(-1)!;
    map.center = { lat: 43.01, lng: -83.61 };
    map.zoom = 15;

    handle.captureView();
    map.center = { lat: 0, lng: 0 };
    map.zoom = 1;
    handle.restoreView();

    expect(map.invalidateSizeCalls).toBe(0);
    animationFrames.shift()?.(0);
    expect(map.invalidateSizeCalls).toBe(1);
    expect(map.setViewCalls).toEqual([
      {
        center: { lat: 43.01, lng: -83.61 },
        zoom: 15,
        options: { animate: false },
      },
    ]);

    handle.destroy();
  });

  it('suppresses configured overlays and tears down external UI exactly once', () => {
    const host = createTestElement();
    const handle = createBaseMap(
      host as unknown as HTMLElement,
      config({
        boundary: { source: 'boundary.geojson' },
        dataLayers: [{ source: 'districts.geojson', label: 'Districts' }],
        imageOverlays: [
          {
            source: 'zoning.png',
            label: 'Zoning',
            bounds: [
              [42.9, -83.7],
              [43.1, -83.5],
            ],
            legend: 'zoning-legend.png',
          },
        ],
      }),
    );
    const map = leaflet.maps.at(-1)!;
    const control = leaflet.layerControls.at(-1)!;
    const image = leaflet.imageOverlays.at(-1)!;

    expect(host.children).toHaveLength(1);
    expect(control.overlays.map(({ label }) => label)).toEqual(['Zoning', 'Districts']);
    expect(image.options).toEqual({ pane: 'dataLayers', opacity: 0.6, interactive: false });
    handle.setOverlaySuppressed(true);
    expect(map.getPane('overlayMarkers')?.style.display).toBe('none');
    expect(map.getPane('tooltipPane')?.style.display).toBe('none');
    expect(map.getPane('dataLayers')?.style.pointerEvents).toBe('none');
    expect(control.container.style.display).toBe('none');
    expect(map.closePopupCalls).toBe(1);

    handle.setOverlaySuppressed(false);
    expect(map.getPane('overlayMarkers')?.style.display).toBe('');
    expect(map.getPane('dataLayers')?.style.pointerEvents).toBe('');
    expect(control.container.style.display).toBe('');

    const boundaryLayers = leaflet.geoJsonLayers.length;
    handle.destroy();
    handle.applyBoundary(boundary);
    handle.restoreView();
    handle.destroy();

    expect(map.removeCalls).toBe(1);
    expect(leaflet.geoJsonLayers).toHaveLength(boundaryLayers);
    expect(control.removed).toBe(true);
    expect(host.children).toHaveLength(0);
    expect(image.handlers.size).toBe(0);
    expect(animationFrames).toHaveLength(0);
  });
});

