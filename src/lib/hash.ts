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
