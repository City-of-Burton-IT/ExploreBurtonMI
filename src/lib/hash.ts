// Pure URL-hash helpers for place permalinks (#map/place/<id>). Kept DOM-free so
// they can be unit-tested and imported by both the store and components.

/** The place id from a `#map/place/<id>` hash, or null. */
export function placeIdFromHash(hash: string): string | null {
  const parts = hash.replace(/^#/, '').split('/');
  return parts[0] === 'map' && parts[1] === 'place' && parts[2]
    ? decodeURIComponent(parts[2])
    : null;
}

/** The hash (without the leading '#') for a place permalink. */
export function placeHash(id: string): string {
  return `map/place/${encodeURIComponent(id)}`;
}

/** The canonical public site origin (trailing slash). Shareable links MUST use this,
 *  never the dev-server localhost or the native capacitor:// origin (#53). The single
 *  source of truth for the origin -- remote.ts and deepLinks.ts derive theirs from it;
 *  kept here so this module stays DOM/Capacitor-free. */
export const SITE_BASE = 'https://explore.burtonmi.gov/';

/** The canonical, shareable URL for a place permalink (always the live site). */
export function placeShareUrl(id: string): string {
  return `${SITE_BASE}#${placeHash(id)}`;
}
