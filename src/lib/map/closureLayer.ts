import L from 'leaflet';
import {
  activeClosures,
  CLOSURE_COLORS,
  closuresGeoJSON,
  type RoadClosure,
} from '../closures';
import { escapeHtml } from './html';

export interface ClosureLayerHandle {
  update(records: RoadClosure[], today: string): RoadClosure[];
  setSuppressed(suppressed: boolean): void;
  destroy(): void;
}

function canonicalRenderKey(record: RoadClosure): string {
  const status = record.status ?? 'full';
  return JSON.stringify([
    record.road,
    record.segment ?? '',
    record.reason ?? '',
    record.start,
    record.end,
    status,
    record.detour ?? '',
    CLOSURE_COLORS[status] ?? CLOSURE_COLORS.full,
    record.geometry?.type ?? '',
    record.geometry?.coordinates ?? null,
  ]);
}

function canonicalActiveClosures(records: RoadClosure[], today: string): RoadClosure[] {
  const unique = new Map<string, RoadClosure>();
  for (const record of activeClosures(records, today)) {
    const key = canonicalRenderKey(record);
    if (!unique.has(key)) unique.set(key, record);
  }
  return [...unique.values()];
}

function renderSignature(collection: ReturnType<typeof closuresGeoJSON>): string {
  const features = collection.features
    .map((feature) => {
      const rendered = feature as {
        geometry: { type: string; coordinates: unknown };
        properties: Record<string, string>;
      };
      const p = rendered.properties;
      return JSON.stringify([
        rendered.geometry.type,
        rendered.geometry.coordinates,
        p.road,
        p.segment,
        p.reason,
        p.start,
        p.end,
        p.status,
        p.detour,
        p._color,
      ]);
    })
    .sort();
  return JSON.stringify(features);
}

function popupHtml(properties: Record<string, string>): string {
  const rows: [string, string][] = [];
  if (properties.segment) rows.push(['Segment', properties.segment]);
  if (properties.reason) rows.push(['Reason', properties.reason]);
  rows.push(['Dates', `${properties.start} to ${properties.end}`]);
  rows.push([
    'Closure',
    properties.status === 'partial' ? 'Partial (lanes affected)' : 'Full',
  ]);
  if (properties.detour) rows.push(['Detour', properties.detour]);

  return (
    `<strong>${escapeHtml(properties.road)}: closed</strong>` +
    rows
      .map(([label, value]) => `<div>${escapeHtml(label)}: ${escapeHtml(value)}</div>`)
      .join('')
  );
}

export function createClosureLayer(map: L.Map): ClosureLayerHandle {
  let layer: L.GeoJSON | undefined;
  let signature: string | undefined;
  let suppressed = false;
  let destroyed = false;

  function removeOwnedLayer(): void {
    if (layer && map.hasLayer(layer)) map.removeLayer(layer);
  }

  return {
    update(records, today) {
      if (destroyed) return [];
      const active = canonicalActiveClosures(records, today);
      const collection = closuresGeoJSON(active);
      const nextSignature = renderSignature(collection);
      if (nextSignature === signature) return active;

      removeOwnedLayer();
      layer = undefined;
      signature = nextSignature;
      if (collection.features.length === 0) return active;

      layer = L.geoJSON(collection as GeoJSON.FeatureCollection, {
        pane: 'overlayMarkers',
        style: (feature) =>
          feature?.geometry.type === 'Point'
            ? {}
            : { color: String(feature?.properties._color), weight: 6, opacity: 0.9 },
        pointToLayer: (feature, latlng) =>
          L.circleMarker(latlng, {
            pane: 'overlayMarkers',
            radius: 9,
            color: '#ffffff',
            weight: 2,
            fillColor: String(feature.properties._color),
            fillOpacity: 0.95,
          }),
        onEachFeature: (feature, featureLayer) => {
          featureLayer.bindPopup(
            popupHtml((feature.properties ?? {}) as Record<string, string>),
          );
        },
      });
      if (!suppressed) layer.addTo(map);
      return active;
    },
    setSuppressed(nextSuppressed) {
      if (destroyed || nextSuppressed === suppressed) return;
      suppressed = nextSuppressed;
      if (suppressed) removeOwnedLayer();
      else if (layer && !map.hasLayer(layer)) layer.addTo(map);
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      removeOwnedLayer();
      layer = undefined;
      signature = undefined;
    },
  };
}

