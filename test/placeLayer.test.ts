import { describe, expect, it, vi } from 'vitest';
import type { PlaceCollection, PlaceFeature } from '../src/lib/types';
import {
  businessPlace,
  governmentPlace,
  mapPresentationConfig,
  offMapPlace,
} from './fixtures/mapPlaces';
import {
  createLeafletTestDouble,
  createTestElement,
  type TestCircleMarker,
  type TestElement,
} from './helpers/leaflet';

const leaflet = createLeafletTestDouble();
vi.doMock('leaflet', () => ({ default: leaflet }));

const { bindClusterPreview } = await import('../src/lib/map/clusterPreview');
const { createPlaceLayer } = await import('../src/lib/map/placeLayer');

function collection(features: PlaceFeature[]): PlaceCollection {
  return { type: 'FeatureCollection', features };
}

function createController(onSelect = vi.fn()) {
  const map = leaflet.map(createTestElement(), { zoom: 12 });
  const markerStart = leaflet.circleMarkers.length;
  const controller = createPlaceLayer(
    map as never,
    collection([governmentPlace, businessPlace, offMapPlace, governmentPlace]),
    mapPresentationConfig,
    onSelect,
  );
  const markers = leaflet.circleMarkers.slice(markerStart);
  const group = leaflet.markerClusterGroups.at(-1)!;
  const markerFor = (id: string): TestCircleMarker =>
    markers.find((marker) => (marker.feature as PlaceFeature | undefined)?.id === id)!;
  return { controller, group, map, markerFor, markers, onSelect };
}

describe('createPlaceLayer', () => {
  it('creates each on-map marker once with its escaped presentation and selection callback', () => {
    const originalFeatures = structuredClone([
      governmentPlace,
      businessPlace,
      offMapPlace,
      governmentPlace,
    ]);
    const { controller, group, map, markerFor, markers, onSelect } = createController();

    expect(markers).toHaveLength(2);
    expect(markerFor(governmentPlace.id).latLng).toEqual([43.002, -83.632]);
    expect(markerFor(governmentPlace.id).options).toEqual({
      radius: 8,
      color: '#ffffff',
      weight: 1.5,
      fillColor: '#1f3a5f',
      fillOpacity: 0.9,
    });
    expect(markerFor(governmentPlace.id).tooltip).toBe('City Hall &lt;Info&gt;');
    expect(group.options).toEqual({ showCoverageOnHover: false, zoomToBoundsOnClick: false });
    expect(map.hasLayer(group)).toBe(true);

    markerFor(governmentPlace.id).fire('click');
    expect(onSelect).toHaveBeenCalledWith(governmentPlace);
    expect([governmentPlace, businessPlace, offMapPlace, governmentPlace]).toEqual(originalFeatures);

    controller.destroy();
  });

  it('reconciles visible marker membership without duplicates', () => {
    const { controller, group } = createController();

    controller.setVisible(new Set([governmentPlace.id, businessPlace.id, offMapPlace.id]));
    expect(group.layers.map((marker) => (marker.feature as PlaceFeature).id)).toEqual([
      governmentPlace.id,
      businessPlace.id,
    ]);

    controller.setVisible(new Set([governmentPlace.id, businessPlace.id]));
    expect(group.layers).toHaveLength(2);

    controller.setVisible(new Set([businessPlace.id]));
    expect(group.layers.map((marker) => (marker.feature as PlaceFeature).id)).toEqual([
      businessPlace.id,
    ]);

    controller.destroy();
  });

  it('restyles only the old and new selections, clears selection, and focuses a marker', () => {
    const { controller, group, markerFor } = createController();
    const governmentMarker = markerFor(governmentPlace.id);
    const businessMarker = markerFor(businessPlace.id);

    controller.setSelected(governmentPlace.id);
    expect(governmentMarker.options).toMatchObject({ radius: 11, color: '#111111', weight: 3 });
    expect(governmentMarker.broughtToFront).toBe(true);

    controller.setSelected(businessPlace.id);
    expect(governmentMarker.options).toMatchObject({ radius: 8, color: '#ffffff', weight: 1.5 });
    expect(businessMarker.options).toMatchObject({ radius: 11, color: '#111111', weight: 3 });
    expect(businessMarker.broughtToFront).toBe(true);

    controller.setSelected(null);
    expect(businessMarker.options).toMatchObject({ radius: 8, color: '#ffffff', weight: 1.5 });

    controller.setVisible(new Set([businessPlace.id]));
    businessMarker.broughtToFront = false;
    controller.focus(businessPlace.id);
    expect(group.zoomToShowLayerCalls).toEqual([businessMarker]);
    expect(businessMarker.broughtToFront).toBe(true);

    controller.destroy();
  });

  it('ignores focus for hidden and filtered markers that are not cluster members', () => {
    const { controller, group, markerFor } = createController();
    const governmentMarker = markerFor(governmentPlace.id);
    const businessMarker = markerFor(businessPlace.id);

    controller.focus(governmentPlace.id);
    controller.setVisible(new Set([governmentPlace.id, businessPlace.id]));
    controller.setVisible(new Set([businessPlace.id]));
    controller.focus(governmentPlace.id);

    expect(group.zoomToShowLayerCalls).toEqual([]);
    expect(governmentMarker.broughtToFront).toBe(false);

    controller.focus(businessPlace.id);
    expect(group.zoomToShowLayerCalls).toEqual([businessMarker]);
    expect(businessMarker.broughtToFront).toBe(true);

    controller.destroy();
  });

  it('runs only the latest suppressed focus after restoring reconciled membership', () => {
    const { controller, group, markerFor } = createController();
    const governmentMarker = markerFor(governmentPlace.id);
    const businessMarker = markerFor(businessPlace.id);
    controller.setVisible(new Set([governmentPlace.id]));

    controller.setSuppressed(true);
    controller.setVisible(new Set([governmentPlace.id, businessPlace.id]));
    controller.setSelected(businessPlace.id);
    controller.focus(governmentPlace.id);
    controller.focus(businessPlace.id);
    businessMarker.broughtToFront = false;
    controller.setSuppressed(false);

    expect(group.layers).toEqual([governmentMarker, businessMarker]);
    expect(group.zoomToShowLayerCalls).toEqual([businessMarker]);
    expect(businessMarker.broughtToFront).toBe(true);

    controller.destroy();
  });

  it('does not complete a deferred focus after destroy', () => {
    const { controller, group, markerFor } = createController();
    const marker = markerFor(governmentPlace.id);
    controller.setVisible(new Set([governmentPlace.id]));
    group.deferZoomToShowLayerCallbacks = true;

    controller.focus(governmentPlace.id);
    controller.destroy();
    group.flushZoomToShowLayerCallbacks();

    expect(marker.broughtToFront).toBe(false);
  });

  it('lets a later focus supersede an earlier deferred callback', () => {
    const { controller, group, markerFor } = createController();
    const governmentMarker = markerFor(governmentPlace.id);
    const businessMarker = markerFor(businessPlace.id);
    controller.setVisible(new Set([governmentPlace.id, businessPlace.id]));
    group.deferZoomToShowLayerCallbacks = true;

    controller.focus(governmentPlace.id);
    controller.focus(businessPlace.id);
    group.flushZoomToShowLayerCallbacks();

    expect(governmentMarker.broughtToFront).toBe(false);
    expect(businessMarker.broughtToFront).toBe(true);

    controller.destroy();
  });

  it('cancels a deferred focus when suppression begins', () => {
    const { controller, group, markerFor } = createController();
    const marker = markerFor(governmentPlace.id);
    controller.setVisible(new Set([governmentPlace.id]));
    group.deferZoomToShowLayerCallbacks = true;

    controller.focus(governmentPlace.id);
    controller.setSuppressed(true);
    group.flushZoomToShowLayerCallbacks();

    expect(marker.broughtToFront).toBe(false);

    controller.destroy();
  });

  it('cancels a deferred focus when cluster membership disappears', () => {
    const { controller, group, markerFor } = createController();
    const marker = markerFor(governmentPlace.id);
    controller.setVisible(new Set([governmentPlace.id]));
    group.deferZoomToShowLayerCallbacks = true;

    controller.focus(governmentPlace.id);
    controller.setVisible(new Set([businessPlace.id]));
    group.flushZoomToShowLayerCallbacks();

    expect(marker.broughtToFront).toBe(false);

    controller.destroy();
  });

  it('restores the latest visible set after suppression and tears down idempotently', () => {
    const { controller, group, map, markerFor, onSelect } = createController();
    controller.setVisible(new Set([governmentPlace.id, businessPlace.id]));

    controller.setSuppressed(true);
    expect(map.hasLayer(group)).toBe(false);
    controller.setVisible(new Set([businessPlace.id]));
    controller.setSuppressed(false);
    controller.setSuppressed(false);

    expect(map.hasLayer(group)).toBe(true);
    expect(group.layers).toEqual([markerFor(businessPlace.id)]);

    controller.destroy();
    const clearCalls = group.clearLayersCalls;
    controller.destroy();
    controller.setVisible(new Set([governmentPlace.id]));
    controller.setSelected(governmentPlace.id);
    controller.focus(governmentPlace.id);
    controller.setSuppressed(false);
    markerFor(governmentPlace.id).fire('click');

    expect(map.hasLayer(group)).toBe(false);
    expect(group.layers).toEqual([]);
    expect(group.clearLayersCalls).toBe(clearCalls);
    expect(group.handlers.size).toBe(0);
    expect(markerFor(governmentPlace.id).handlers.size).toBe(0);
    expect(markerFor(businessPlace.id).handlers.size).toBe(0);
    expect(markerFor(governmentPlace.id)).toMatchObject({
      tooltipBound: false,
      closeTooltipCalls: 1,
      unbindTooltipCalls: 1,
    });
    expect(markerFor(businessPlace.id)).toMatchObject({
      tooltipBound: false,
      closeTooltipCalls: 1,
      unbindTooltipCalls: 1,
    });
    expect(onSelect).not.toHaveBeenCalled();
  });
});

describe('bindClusterPreview', () => {
  it('uses the injected selection callback and disposes group, button, and popup artifacts', () => {
    const map = leaflet.map(createTestElement(), { zoom: 12 });
    const group = leaflet.markerClusterGroup();
    const selected: PlaceFeature[] = [];
    let popupContent: TestElement | undefined;
    let tooltipBound = false;
    let popupBound = false;
    const cluster = {
      getAllChildMarkers: () => [
        { feature: governmentPlace },
        { feature: businessPlace },
      ],
      getChildCount: () => 2,
      getBounds: () => ({ id: 'bounds' }),
      bindTooltip: () => {
        tooltipBound = true;
        return cluster;
      },
      openTooltip: () => cluster,
      closeTooltip: () => cluster,
      unbindTooltip: () => {
        tooltipBound = false;
        return cluster;
      },
      bindPopup: (content: TestElement) => {
        popupBound = true;
        popupContent = content;
        return cluster;
      },
      openPopup: () => cluster,
      closePopup: () => cluster,
      unbindPopup: () => {
        popupBound = false;
        return cluster;
      },
    };

    const dispose = bindClusterPreview(
      map as never,
      group as never,
      (feature: PlaceFeature) => selected.push(feature),
    );
    group.fire('clustermouseover', { layer: cluster });
    group.fire('clusterclick', { layer: cluster });

    const button = popupContent!.children[1].children[0].children[0];
    for (const handler of button.listeners.get('click') ?? []) handler({});
    expect(selected).toEqual([governmentPlace]);
    expect(map.closePopupCalls).toBe(1);
    expect(tooltipBound).toBe(true);
    expect(popupBound).toBe(true);

    dispose();
    dispose();

    expect(group.handlers.size).toBe(0);
    expect(button.listeners.has('click')).toBe(false);
    expect(tooltipBound).toBe(false);
    expect(popupBound).toBe(false);
  });
});

