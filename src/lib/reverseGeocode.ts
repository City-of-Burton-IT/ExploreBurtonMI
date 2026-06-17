// Reverse-geocode a dropped pin to the nearest known street address (#71).
//
// PRIVACY: this runs entirely on the device. The resident's dropped-pin
// coordinates are matched against a committed, city-owned address table
// (public/address-points.json) -- they are NEVER sent to a third-party
// geocoder. Nothing leaves the device until the resident submits the report.
//
// The table is a compact lookup (a flat array, not a drawn map layer), built
// out-of-band from a Burton Assessing address export -- see
// tools/build_address_points.py. A linear nearest-neighbour scan over the
// ~13k city points is sub-millisecond and only runs once per pin-drop, so no
// spatial index is warranted.

import { dataFetch } from './remote';

export interface AddressPoint {
  lat: number;
  lng: number;
  address: string;
}

/** Default reject radius: if the nearest known address is farther than this,
 *  auto-fill would be misleading, so we return null and let the resident type. */
export const DEFAULT_MAX_DISTANCE_M = 250;

const EARTH_RADIUS_M = 6_371_000;
const toRad = (deg: number): number => (deg * Math.PI) / 180;

/** Great-circle distance between two lat/lng points, in metres. */
export function haversineMeters(
  aLat: number,
  aLng: number,
  bLat: number,
  bLng: number,
): number {
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const sinLat = Math.sin(dLat / 2);
  const sinLng = Math.sin(dLng / 2);
  const h =
    sinLat * sinLat + Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * sinLng * sinLng;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Parse the committed compact table `{ points: [[lat, lng, address], ...] }`
 *  into AddressPoint[]. Tolerant: malformed rows are skipped, not fatal. */
export function parseAddressPoints(json: unknown): AddressPoint[] {
  const rows = (json as { points?: unknown })?.points;
  if (!Array.isArray(rows)) return [];
  const out: AddressPoint[] = [];
  for (const row of rows) {
    if (!Array.isArray(row) || row.length < 3) continue;
    const [lat, lng, address] = row;
    if (typeof lat !== 'number' || !Number.isFinite(lat)) continue;
    if (typeof lng !== 'number' || !Number.isFinite(lng)) continue;
    if (typeof address !== 'string' || address.trim() === '') continue;
    out.push({ lat, lng, address: address.trim() });
  }
  return out;
}

export interface NearestResult {
  address: string;
  distanceM: number;
}

/** Nearest known address to (lat, lng), or null if the list is empty or the
 *  closest point is beyond maxDistanceM. */
export function nearestAddress(
  lat: number,
  lng: number,
  points: readonly AddressPoint[],
  maxDistanceM: number = DEFAULT_MAX_DISTANCE_M,
): NearestResult | null {
  let best: NearestResult | null = null;
  for (const p of points) {
    const d = haversineMeters(lat, lng, p.lat, p.lng);
    if (best === null || d < best.distanceM) best = { address: p.address, distanceM: d };
  }
  if (best === null || best.distanceM > maxDistanceM) return null;
  return best;
}

// Load the committed address table once, then reuse it for every subsequent
// pin-drop in the session. A failed load (offline, file missing) resolves to []
// so the caller silently falls back to manual address entry -- never throws.
let cache: Promise<AddressPoint[]> | null = null;

export function loadAddressPoints(source: string): Promise<AddressPoint[]> {
  if (cache) return cache;
  cache = dataFetch(source)
    .then((r) => (r.ok ? r.json() : null))
    .then((json) => parseAddressPoints(json))
    .catch(() => []);
  return cache;
}

/** Test-only: drop the cached table so a fresh load can be exercised. */
export function _resetAddressPointCache(): void {
  cache = null;
}
