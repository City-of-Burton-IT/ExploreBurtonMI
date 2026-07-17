import { describe, expect, it, vi } from 'vitest';
import type { RoadClosure } from '../src/lib/closures';

interface FakeFeatureLayer {
  popup?: string;
  bindPopup(content: string): FakeFeatureLayer;
}

interface FakeGeoJsonLayer {
  source: GeoJSON.FeatureCollection;
  options: Record<string, unknown>;
  featureLayers: FakeFeatureLayer[];
  addTo(map: FakeMap): FakeGeoJsonLayer;
}

class FakeMap {
  readonly layers = new Set<object>();
  readonly added: object[] = [];
  readonly removed: object[] = [];

  addLayer(layer: object): this {
    this.layers.add(layer);
    this.added.push(layer);
    return this;
  }

  removeLayer(layer: object): this {
    this.layers.delete(layer);
    this.removed.push(layer);
    return this;
  }

  hasLayer(layer: object): boolean {
    return this.layers.has(layer);
  }
}

function popupLayer(): FakeFeatureLayer {
  return {
    bindPopup(content) {
      this.popup = content;
      return this;
    },
  };
}

const leaflet = {
  geoJsonLayers: [] as FakeGeoJsonLayer[],
  circleMarkers: [] as (FakeFeatureLayer & { latlng: unknown; options: Record<string, unknown> })[],
  geoJSON(source: GeoJSON.FeatureCollection, options: Record<string, unknown>): FakeGeoJsonLayer {
    const onEachFeature = options.onEachFeature as
      | ((feature: GeoJSON.Feature, layer: FakeFeatureLayer) => void)
      | undefined;
    const pointToLayer = options.pointToLayer as
      | ((feature: GeoJSON.Feature, latlng: [number, number]) => FakeFeatureLayer)
      | undefined;
    const featureLayers = source.features.map((feature) => {
      const coordinates = feature.geometry.type === 'Point' ? feature.geometry.coordinates : undefined;
      const layer =
        coordinates && pointToLayer
          ? pointToLayer(feature, [coordinates[1], coordinates[0]])
          : popupLayer();
      onEachFeature?.(feature, layer);
      return layer;
    });
    const layer: FakeGeoJsonLayer = {
      source,
      options,
      featureLayers,
      addTo(map) {
        map.addLayer(this);
        return this;
      },
    };
    this.geoJsonLayers.push(layer);
    return layer;
  },
  circleMarker(latlng: unknown, options: Record<string, unknown>) {
    const marker = Object.assign(popupLayer(), { latlng, options });
    this.circleMarkers.push(marker);
    return marker;
  },
};

vi.doMock('leaflet', () => ({ default: leaflet }));

const { createClosureLayer } = await import('../src/lib/map/closureLayer');

const lineGeometry: RoadClosure['geometry'] = {
  type: 'LineString',
  coordinates: [
    [-83.6, 42.99],
    [-83.62, 42.99],
  ],
};

const pointGeometry: RoadClosure['geometry'] = {
  type: 'Point',
  coordinates: [-83.63, 43.0],
};

function closure(overrides: Partial<RoadClosure> = {}): RoadClosure {
  return {
    road: 'Maple Rd',
    segment: 'Center Rd to Belsay Rd',
    reason: 'Water main replacement',
    start: '2026-06-10',
    end: '2026-06-20',
    status: 'full',
    detour: 'Use Bristol Rd',
    geometry: lineGeometry,
    ...overrides,
  };
}

function createController() {
  const map = new FakeMap();
  const layerStart = leaflet.geoJsonLayers.length;
  const markerStart = leaflet.circleMarkers.length;
  const controller = createClosureLayer(map as never);
  return {
    controller,
    map,
    layers: () => leaflet.geoJsonLayers.slice(layerStart),
    markers: () => leaflet.circleMarkers.slice(markerStart),
  };
}

describe('createClosureLayer', () => {
  it('returns the active records and projects only their mapped geometry with existing styles', () => {
    const { controller, layers, markers } = createController();
    const activeLine = closure();
    const activePoint = closure({ road: 'Genesee Rd', status: 'partial', geometry: pointGeometry });
    const activeWithoutGeometry = closure({ road: 'Atherton Rd', geometry: undefined });
    const future = closure({ road: 'Future Rd', start: '2026-07-01', end: '2026-07-02' });

    const active = controller.update(
      [future, activeLine, activeWithoutGeometry, activePoint],
      '2026-06-15',
    );

    expect(active).toEqual([activeLine, activeWithoutGeometry, activePoint]);
    expect(layers()).toHaveLength(1);
    expect(layers()[0].source.features).toHaveLength(2);
    expect(layers()[0].options.pane).toBe('overlayMarkers');
    const style = layers()[0].options.style as (feature: GeoJSON.Feature) => object;
    expect(style(layers()[0].source.features[0])).toEqual({
      color: '#d93025',
      weight: 6,
      opacity: 0.9,
    });
    expect(style(layers()[0].source.features[1])).toEqual({});
    expect(markers()[0]).toMatchObject({
      latlng: [43, -83.63],
      options: {
        pane: 'overlayMarkers',
        radius: 9,
        color: '#ffffff',
        weight: 2,
        fillColor: '#f29900',
        fillOpacity: 0.95,
      },
    });

    controller.destroy();
  });

  it('returns reordered unique records in source order without replacing the layer', () => {
    const { controller, layers, map } = createController();
    const first = closure();
    const second = closure({ road: 'Genesee Rd', geometry: pointGeometry });

    expect(controller.update([first, second], '2026-06-15')).toEqual([first, second]);
    const originalLayer = layers()[0];
    const reordered = controller.update(
      [structuredClone(second), structuredClone(first)],
      '2026-06-15',
    );

    expect(reordered).toEqual([second, first]);
    expect(layers()).toEqual([originalLayer]);
    expect(map.layers).toEqual(new Set([originalLayer]));
    expect(map.removed).toEqual([]);

    controller.destroy();
  });

  it('returns and renders one canonical record for cloned duplicates', () => {
    const { controller, layers } = createController();
    const original = closure();
    const duplicate = structuredClone(original);

    const active = controller.update([original, duplicate], '2026-06-15');

    expect(active).toHaveLength(1);
    expect(active[0]).toBe(original);
    expect(layers()).toHaveLength(1);
    expect(layers()[0].source.features).toHaveLength(1);

    controller.destroy();
  });

  it('does not replace the canonical rendering when a cloned duplicate is removed', () => {
    const { controller, layers, map } = createController();
    const original = closure();

    controller.update([original, structuredClone(original)], '2026-06-15');
    const originalLayer = layers()[0];
    const remaining = structuredClone(original);
    const active = controller.update([remaining], '2026-06-15');

    expect(active).toHaveLength(1);
    expect(active[0]).toBe(remaining);
    expect(layers()).toEqual([originalLayer]);
    expect(map.removed).toEqual([]);

    controller.destroy();
  });

  it('preserves source order for unique canonical records', () => {
    const { controller } = createController();
    const maple = closure();
    const genesee = closure({ road: 'Genesee Rd', geometry: pointGeometry });
    const atherton = closure({ road: 'Atherton Rd', geometry: undefined });

    const forward = controller.update([maple, genesee, atherton], '2026-06-15');
    const reversed = controller.update(
      [structuredClone(atherton), structuredClone(genesee), structuredClone(maple)],
      '2026-06-15',
    );

    expect(forward).toEqual([maple, genesee, atherton]);
    expect(reversed).toEqual([atherton, genesee, maple]);

    controller.destroy();
  });

  it.each([
    ['geometry', { geometry: pointGeometry }],
    ['road', { road: 'Genesee Rd' }],
    ['segment', { segment: 'Belsay Rd to Vassar Rd' }],
    ['reason', { reason: 'Bridge repair' }],
    ['start', { start: '2026-06-11' }],
    ['end', { end: '2026-06-19' }],
    ['status/style color', { status: 'partial' as const }],
    ['detour', { detour: 'Use Atherton Rd' }],
  ])('retains canonical records when rendered %s differs', (_field, changed) => {
    const { controller, layers } = createController();

    const active = controller.update([closure(), closure(changed)], '2026-06-15');

    expect(active).toHaveLength(2);
    expect(layers()[0].source.features).toHaveLength(2);

    controller.destroy();
  });

  it.each([
    ['geometry', { geometry: pointGeometry }],
    ['road', { road: 'Genesee Rd' }],
    ['segment', { segment: 'Belsay Rd to Vassar Rd' }],
    ['reason', { reason: 'Bridge repair' }],
    ['start', { start: '2026-06-11' }],
    ['end', { end: '2026-06-19' }],
    ['status', { status: 'partial' as const }],
    ['detour', { detour: 'Use Atherton Rd' }],
  ])('replaces stale rendering when %s changes', (_field, changed) => {
    const { controller, layers, map } = createController();
    controller.update([closure()], '2026-06-15');
    const oldLayer = layers()[0];

    controller.update([closure(changed)], '2026-06-15');

    expect(layers()).toHaveLength(2);
    expect(map.hasLayer(oldLayer)).toBe(false);
    expect(map.layers).toEqual(new Set([layers()[1]]));
    expect(map.removed).toEqual([oldLayer]);

    controller.destroy();
  });

  it('escapes every record value included in popup HTML', () => {
    const { controller, layers } = createController();
    controller.update(
      [
        closure({
          road: `<Road & "A" 'B'>`,
          segment: '<Segment & one>',
          reason: '<Reason & two>',
          start: '2026-06-10<script>',
          end: '2026-06-20</script>',
          status: 'partial',
          detour: '<Detour & three>',
        }),
      ],
      '2026-06-15',
    );

    expect(layers()[0].featureLayers[0].popup).toBe(
      '<strong>&lt;Road &amp; &quot;A&quot; &#39;B&#39;&gt;: closed</strong>' +
        '<div>Segment: &lt;Segment &amp; one&gt;</div>' +
        '<div>Reason: &lt;Reason &amp; two&gt;</div>' +
        '<div>Dates: 2026-06-10&lt;script&gt; to 2026-06-20&lt;/script&gt;</div>' +
        '<div>Closure: Partial (lanes affected)</div>' +
        '<div>Detour: &lt;Detour &amp; three&gt;</div>',
    );

    controller.destroy();
  });

  it('escapes entity-like popup values exactly once', () => {
    const { controller, layers } = createController();
    controller.update(
      [closure({ reason: 'Repair &amp; restoration' })],
      '2026-06-15',
    );

    const popup = layers()[0].featureLayers[0].popup;
    expect(popup).toContain('Reason: Repair &amp;amp; restoration');
    expect(popup).not.toContain('Repair &amp;amp;amp; restoration');

    controller.destroy();
  });

  it('removes the rendered layer when unchanged records become inactive', () => {
    const { controller, layers, map } = createController();
    const records = [closure({ start: '2026-06-20', end: '2026-06-20' })];

    expect(controller.update(records, '2026-06-20')).toEqual(records);
    const activeLayer = layers()[0];
    expect(controller.update(records, '2026-06-21')).toEqual([]);

    expect(layers()).toEqual([activeLayer]);
    expect(map.hasLayer(activeLayer)).toBe(false);
    expect(map.removed).toEqual([activeLayer]);

    controller.destroy();
  });

  it('renders a layer when unchanged records become active', () => {
    const { controller, layers, map } = createController();
    const records = [closure({ start: '2026-06-20', end: '2026-06-20' })];

    expect(controller.update(records, '2026-06-19')).toEqual([]);
    expect(layers()).toEqual([]);
    expect(controller.update(records, '2026-06-20')).toEqual(records);

    expect(layers()).toHaveLength(1);
    expect(map.layers).toEqual(new Set([layers()[0]]));

    controller.destroy();
  });

  it('removes the owned layer while suppressed and restores only the latest rendering', () => {
    const { controller, layers, map } = createController();
    controller.update([closure()], '2026-06-15');
    const firstLayer = layers()[0];

    controller.setSuppressed(true);
    controller.setSuppressed(true);
    controller.update([closure({ reason: 'Updated while hidden' })], '2026-06-15');
    const latestLayer = layers()[1];

    expect(map.hasLayer(firstLayer)).toBe(false);
    expect(map.hasLayer(latestLayer)).toBe(false);
    expect(map.removed).toEqual([firstLayer]);

    controller.setSuppressed(false);
    controller.setSuppressed(false);

    expect(map.layers).toEqual(new Set([latestLayer]));
    expect(map.added).toEqual([firstLayer, latestLayer]);

    controller.destroy();
  });

  it('tears down only its owned layer and ignores repeated destroy or later updates', () => {
    const { controller, layers, map } = createController();
    const externalLayer = { kind: 'external' };
    map.addLayer(externalLayer);
    controller.update([closure()], '2026-06-15');
    const ownedLayer = layers()[0];

    controller.destroy();
    controller.destroy();
    controller.setSuppressed(true);
    controller.setSuppressed(false);
    expect(controller.update([closure({ road: 'Later Rd' })], '2026-06-15')).toEqual([]);

    expect(map.layers).toEqual(new Set([externalLayer]));
    expect(map.removed).toEqual([ownedLayer]);
    expect(layers()).toEqual([ownedLayer]);
  });
});

