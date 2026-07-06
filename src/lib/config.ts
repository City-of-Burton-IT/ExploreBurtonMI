import type { AppConfig } from './types';
import { dataFetch } from './remote';

/**
 * Load and validate public/config.json.
 *
 * Validation fails LOUDLY (throws) on a malformed config rather than silently
 * rendering a broken map - this is the deliberate fix for the original Finda
 * app, where config could reference missing fields with no warning.
 */
export async function loadConfig(url = 'config.json'): Promise<AppConfig> {
  const res = await dataFetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load ${url}: HTTP ${res.status}`);
  }
  const raw = (await res.json()) as unknown;
  return validateConfig(raw);
}

export function validateConfig(raw: unknown): AppConfig {
  const errors: string[] = [];
  const c = raw as Partial<AppConfig>;

  if (!c || typeof c !== 'object') {
    throw new Error('config.json is not an object');
  }
  if (!c.project?.name) errors.push('project.name is required');
  if (!c.project?.tagline) errors.push('project.tagline is required');

  if (!c.data?.source) errors.push('data.source is required');

  if (!c.map) {
    errors.push('map is required');
  } else {
    if (!isLatLng(c.map.center)) errors.push('map.center must be [lat, lng]');
    if (typeof c.map.zoom !== 'number') errors.push('map.zoom must be a number');
    if (typeof c.map.maxZoom !== 'number') errors.push('map.maxZoom must be a number');
    if (typeof c.map.minZoom !== 'number') errors.push('map.minZoom must be a number');
    if (!isBounds(c.map.maxBounds)) {
      errors.push('map.maxBounds must be [[lat, lng], [lat, lng]]');
    }
    if (!c.map.previewAttribute) errors.push('map.previewAttribute is required');
  }

  if (!c.tiles?.url) errors.push('tiles.url is required');
  if (!c.tiles?.attribution) errors.push('tiles.attribution is required');

  if (!c.categoryField) errors.push('categoryField is required');
  if (!isPlainObject(c.categories)) {
    errors.push('categories must be an object');
  } else if (
    Object.values(c.categories).some((v) => !isPlainObject(v) || !(v as { color?: unknown }).color)
  ) {
    errors.push('categories entries must each have a color');
  }

  if (!Array.isArray(c.properties)) {
    errors.push('properties must be an array');
  } else if (
    c.properties.some((p) => !p || typeof p.field !== 'string' || !p.field || typeof p.label !== 'string' || !p.label)
  ) {
    errors.push('properties entries must each have a field and a label');
  }

  if (!isPlainObject(c.facets)) {
    errors.push('facets must be an object');
  } else if (
    Object.values(c.facets).some(
      (f) =>
        !isPlainObject(f) ||
        typeof (f as { title?: unknown }).title !== 'string' ||
        !(f as { title?: unknown }).title ||
        ((f as { type?: unknown }).type !== 'single' && (f as { type?: unknown }).type !== 'list'),
    )
  ) {
    errors.push('facets entries must each have a title and a type of "single" or "list"');
  }

  if (!Array.isArray(c.list) || c.list.some((f) => typeof f !== 'string' || !f)) {
    errors.push('list must be an array of field names');
  }

  if (!Array.isArray(c.search?.keys) || c.search.keys.some((k) => typeof k !== 'string' || !k)) {
    errors.push('search.keys must be an array of field names');
  }

  if (errors.length) {
    throw new Error(`Invalid config.json:\n - ${errors.join('\n - ')}`);
  }
  return c as AppConfig;
}

function isLatLng(v: unknown): v is [number, number] {
  return (
    Array.isArray(v) &&
    v.length === 2 &&
    typeof v[0] === 'number' &&
    typeof v[1] === 'number'
  );
}

function isBounds(v: unknown): v is [[number, number], [number, number]] {
  return Array.isArray(v) && v.length === 2 && isLatLng(v[0]) && isLatLng(v[1]);
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}
