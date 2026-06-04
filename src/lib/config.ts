import type { AppConfig } from './types';

/**
 * Load and validate public/config.json.
 *
 * Validation fails LOUDLY (throws) on a malformed config rather than silently
 * rendering a broken map - this is the deliberate fix for the original Finda
 * app, where config could reference missing fields with no warning.
 */
export async function loadConfig(url = 'config.json'): Promise<AppConfig> {
  const res = await fetch(url);
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
  if (!c.map) {
    errors.push('map is required');
  } else {
    if (!isLatLng(c.map.center)) errors.push('map.center must be [lat, lng]');
    if (typeof c.map.zoom !== 'number') errors.push('map.zoom must be a number');
  }
  if (!c.tiles?.url) errors.push('tiles.url is required');

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
