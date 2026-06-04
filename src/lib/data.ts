import type { PlaceCollection, PlaceFeature } from './types';

/**
 * Load and validate the GeoJSON dataset. Fails LOUDLY on a malformed file
 * rather than silently dropping points. Assigns a stable string `id` to any
 * feature that lacks one (used to sync map <-> list <-> filter).
 */
export async function loadData(url: string): Promise<PlaceCollection> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load ${url}: HTTP ${res.status}`);
  }
  const raw = (await res.json()) as unknown;
  return validateData(raw);
}

export function validateData(raw: unknown): PlaceCollection {
  const fc = raw as Partial<PlaceCollection>;
  if (!fc || fc.type !== 'FeatureCollection' || !Array.isArray(fc.features)) {
    throw new Error('data is not a GeoJSON FeatureCollection');
  }

  const features: PlaceFeature[] = fc.features.map((f, i) => {
    const coords = f?.geometry?.coordinates;
    const validPoint =
      f?.geometry?.type === 'Point' &&
      Array.isArray(coords) &&
      coords.length === 2 &&
      typeof coords[0] === 'number' &&
      typeof coords[1] === 'number';
    if (!validPoint) {
      throw new Error(`feature[${i}] is not a valid Point geometry`);
    }
    if (!f.properties?.name) {
      throw new Error(`feature[${i}] is missing properties.name`);
    }
    return {
      ...f,
      id: f.id != null ? String(f.id) : `eb-${i}`,
    } as PlaceFeature;
  });

  return { type: 'FeatureCollection', features };
}
